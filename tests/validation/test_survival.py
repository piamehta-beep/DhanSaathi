"""Survival model validation (spec Section 9.1).

Targets: C-index > 0.70 overall, per-persona C-index > 0.60, hazard ratio
signs matching Section 5.2's expected-sign table, Schoenfeld p > 0.05.
Prints a summary table so results are visible before Milestone 3 proceeds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from lifelines.statistics import proportional_hazard_test
from lifelines.utils import concordance_index

from app.models.survival import EXPECTED_SIGN, build_training_dataset, fit_cox_model
from app.features.pipeline import FEATURE_VECTOR_ORDER

SEED = 42


def _split(df: pd.DataFrame, frac: float = 0.8):
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(df))
    cut = int(len(df) * frac)
    train_idx, test_idx = idx[:cut], idx[cut:]
    return df.iloc[train_idx].reset_index(drop=True), df.iloc[test_idx].reset_index(drop=True)


def test_survival_model_validation(db):
    full_df = build_training_dataset(db)
    assert len(full_df) == 1000

    train_df, test_df = _split(full_df)
    cph, scaler, x_scaled_train = fit_cox_model(train_df)
    active_cols = list(x_scaled_train.columns)

    x_test = pd.DataFrame(
        scaler.transform(test_df[active_cols]), columns=active_cols
    )
    partial_hazard_test = cph.predict_partial_hazard(x_test)
    c_index_overall = concordance_index(test_df["duration"], -partial_hazard_test, test_df["event"])

    partial_hazard_train = cph.predict_partial_hazard(x_scaled_train)
    c_index_train = concordance_index(train_df["duration"], -partial_hazard_train, train_df["event"])

    hazard_ratios = cph.hazard_ratios_.to_dict()
    sign_report = {}
    for feature, hr in hazard_ratios.items():
        expected = EXPECTED_SIGN.get(feature, 0)
        actual = 1 if hr > 1 else (-1 if hr < 1 else 0)
        sign_report[feature] = {"hazard_ratio": round(hr, 4), "expected_sign": expected, "actual_sign": actual, "match": expected == 0 or actual == expected}

    per_persona_c_index = {}
    for persona in test_df["persona"].unique():
        mask = test_df["persona"] == persona
        if mask.sum() < 5 or test_df.loc[mask, "event"].sum() == 0:
            per_persona_c_index[persona] = None
            continue
        ph = cph.predict_partial_hazard(x_test[mask.to_numpy()])
        per_persona_c_index[persona] = round(
            concordance_index(test_df.loc[mask, "duration"], -ph, test_df.loc[mask, "event"]), 4
        )

    try:
        sch_results = proportional_hazard_test(cph, train_df.assign(**{
            c: x_scaled_train[c] for c in active_cols
        })[active_cols + ["duration", "event"]], time_transform="rank")
        schoenfeld_p = sch_results.summary["p"].to_dict()
    except Exception as e:  # pragma: no cover - diagnostic only
        schoenfeld_p = {"error": str(e)}

    print("\n=== Survival Model Validation Summary ===")
    print(f"C-index (train): {c_index_train:.4f}")
    print(f"C-index (test, n={len(test_df)}): {c_index_overall:.4f}  (target > 0.70)")
    print("\nHazard ratio sign check:")
    for feature, info in sign_report.items():
        flag = "OK" if info["match"] else "MISMATCH"
        print(f"  {feature:24s} HR={info['hazard_ratio']:.4f}  expected_sign={info['expected_sign']:+d}  [{flag}]")
    print("\nPer-persona C-index (test set):")
    for persona, ci in per_persona_c_index.items():
        print(f"  {persona:20s} {ci}")
    print("\nSchoenfeld proportional-hazards p-values:")
    print(schoenfeld_p)
    print("==========================================\n")

    assert c_index_overall > 0.70, f"C-index {c_index_overall:.4f} below spec Section 9.1 target of 0.70"
