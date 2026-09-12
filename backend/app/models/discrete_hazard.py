"""Discrete-time hazard model — the spec Section 5.2 fallback for when Cox PH
fails the proportional-hazards assumption.

Model:
    logit(h_t) = alpha_t + beta' X,
    where h_t = P(event at month t | survived to month t)

Because alpha_t is free per time point, the baseline hazard can take any shape
over time — this is exactly what relaxes the proportional-hazards constraint
that the Cox model imposes (and that dbr, runway_trend and savings_rate were
found to violate via the Schoenfeld test).

Implementation note: the spec's formula has a time-varying intercept
(alpha_t) but a *constant* coefficient vector (beta), which is the pooled
person-period logistic model implemented here — one row per
(customer, month-at-risk), with month dummies supplying alpha_t. The spec's
parenthetical library hint ("LogisticRegression with one model per time
point") would instead give time-varying beta_t, a different and much less
stable model on 1,000 customers. The formula is the more precise
specification, so it is the one implemented.

Survival is recovered from the fitted hazards as
    S(t) = prod_{k=1..t} (1 - h_k).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

MAX_MONTHS = 18
C_REGULARIZATION = 1.0


def to_person_period(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    """Expand one-row-per-customer survival data into person-period format.

    A customer with duration d contributes d rows (months 1..d); the event
    indicator is 1 only on the final row, and only if they were not censored.
    """
    rows = []
    events = []
    for _, r in df.iterrows():
        duration = int(r["duration"])
        event = int(r["event"])
        for t in range(1, duration + 1):
            rows.append({**{c: r[c] for c in feature_cols}, "month": t})
            events.append(1 if (t == duration and event == 1) else 0)
    return pd.DataFrame(rows), np.array(events)


def _design_matrix(pp: pd.DataFrame, feature_cols: list[str], scaler: StandardScaler, fit: bool) -> np.ndarray:
    x_features = pp[feature_cols].to_numpy(dtype=float)
    x_features = scaler.fit_transform(x_features) if fit else scaler.transform(x_features)

    month_idx = pp["month"].to_numpy(dtype=int) - 1
    month_dummies = np.zeros((len(pp), MAX_MONTHS))
    month_dummies[np.arange(len(pp)), np.clip(month_idx, 0, MAX_MONTHS - 1)] = 1.0

    return np.hstack([x_features, month_dummies])


class DiscreteTimeHazardModel:
    def __init__(self, feature_cols: list[str]):
        self.feature_cols = feature_cols
        self.scaler = StandardScaler()
        self.clf = LogisticRegression(
            C=C_REGULARIZATION, max_iter=2000, fit_intercept=False, solver="lbfgs"
        )

    def fit(self, df: pd.DataFrame) -> "DiscreteTimeHazardModel":
        pp, events = to_person_period(df, self.feature_cols)
        x = _design_matrix(pp, self.feature_cols, self.scaler, fit=True)
        self.clf.fit(x, events)
        return self

    @property
    def beta(self) -> dict[str, float]:
        """Covariate coefficients (excludes the month-dummy intercepts)."""
        coefs = self.clf.coef_[0][: len(self.feature_cols)]
        return dict(zip(self.feature_cols, coefs.tolist()))

    def hazard_ratios(self) -> dict[str, float]:
        """exp(beta) — an odds ratio here rather than a hazard ratio, but
        directionally interpretable the same way (>1 raises risk)."""
        return {k: float(np.exp(v)) for k, v in self.beta.items()}

    def baseline_hazards(self) -> np.ndarray:
        """alpha_t as fitted month intercepts, converted to baseline hazards."""
        alphas = self.clf.coef_[0][len(self.feature_cols):]
        return 1.0 / (1.0 + np.exp(-alphas))

    def predict_hazards(self, features_row: dict, months: int = 12) -> np.ndarray:
        x_features = np.array([[float(features_row.get(c) or 0.0) for c in self.feature_cols]])
        x_scaled = self.scaler.transform(x_features)[0]

        hazards = np.empty(months)
        for t in range(months):
            month_dummy = np.zeros(MAX_MONTHS)
            month_dummy[min(t, MAX_MONTHS - 1)] = 1.0
            z = float(self.clf.coef_[0] @ np.concatenate([x_scaled, month_dummy]))
            hazards[t] = 1.0 / (1.0 + np.exp(-z))
        return hazards

    def predict_survival(self, features_row: dict, months: int = 12) -> np.ndarray:
        return np.cumprod(1.0 - self.predict_hazards(features_row, months))

    def risk_score(self, df: pd.DataFrame) -> np.ndarray:
        """Time-invariant linear predictor beta'X — the ranking used for
        concordance, directly comparable to the Cox partial hazard."""
        x = df[self.feature_cols].to_numpy(dtype=float)
        x_scaled = self.scaler.transform(x)
        beta = self.clf.coef_[0][: len(self.feature_cols)]
        return x_scaled @ beta
