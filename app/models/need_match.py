"""Need-match classifier (spec Section 5.3, `need_match` component).

An XGBoost multiclass model over the standard feature vector, predicting
which product category a customer most plausibly needs. Its output is the
predicted probability for the product being scored, which enters CBS with
weight 0.30.

Training labels come from persona-appropriate product needs, which makes
this a deliberately weak supervisory signal — it encodes the designers' prior
about who needs what, not observed customer outcomes (the synthetic dataset
has no take-up or satisfaction data to learn from). It is used only as one
weighted term in the objective, and it can never override the safety gate.
A production system would replace these labels with realised outcomes.
"""

from __future__ import annotations

import threading

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from xgboost import XGBClassifier

from app.database.models import Customer
from app.features.pipeline import FEATURE_VECTOR_ORDER, compute_features, feature_vector

# Persona -> the product need the design considers most appropriate. These are
# priors, not ground truth; see the module docstring.
#
# No persona is labelled `personal_loan`: a borrowing need arises from an
# expressed funding requirement (a purchase, a consolidation, an emergency),
# and the synthetic dataset contains no such signal, so there is nothing
# honest to learn from. Personal loans therefore always score need_match = 0
# and must win on affordability and life-stage alignment alone. That is a
# real limitation of the data, recorded here rather than papered over with an
# invented label.
PERSONA_NEED_LABEL = {
    "stable_salaried": "mutual_fund_sip",
    "young_earner": "credit_card",      # early_career: building credit history
    "gig_worker": "term_insurance",     # volatile income: protection first
    "near_retirement": "term_insurance",
    "over_leveraged": "no_action",
    "distressed": "no_action",
}

# XGBoost requires contiguous class indices, so the class list is derived from
# the labels actually used rather than declared up front.
PRODUCT_CLASSES = sorted(set(PERSONA_NEED_LABEL.values()))

RANDOM_STATE = 42


class NeedMatchModel:
    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.clf = XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.1,
            subsample=0.9, colsample_bytree=0.9,
            objective="multi:softprob", num_class=len(PRODUCT_CLASSES),
            random_state=RANDOM_STATE, eval_metric="mlogloss",
        )
        self.classes = PRODUCT_CLASSES

    def fit(self, x: pd.DataFrame, y: np.ndarray) -> "NeedMatchModel":
        x_scaled = self.scaler.fit_transform(x)
        self.clf.fit(x_scaled, y)
        return self

    def predict_proba(self, features: dict) -> dict[str, float]:
        vec = np.array([feature_vector(features)])
        probs = self.clf.predict_proba(self.scaler.transform(vec))[0]
        return {cls: float(p) for cls, p in zip(self.classes, probs)}


def build_need_dataset(db: Session) -> tuple[pd.DataFrame, np.ndarray]:
    rows, labels = [], []
    for customer in db.query(Customer).all():
        features = compute_features(db, customer.id, persist=False)
        rows.append(dict(zip(FEATURE_VECTOR_ORDER, feature_vector(features))))
        labels.append(PRODUCT_CLASSES.index(PERSONA_NEED_LABEL[customer.persona]))
    return pd.DataFrame(rows), np.array(labels)


_lock = threading.Lock()
_cache: dict = {}


def get_or_train_need_model(db: Session) -> NeedMatchModel:
    with _lock:
        if "model" not in _cache:
            x, y = build_need_dataset(db)
            _cache["model"] = NeedMatchModel().fit(x, y)
        return _cache["model"]


def reset_need_model_cache() -> None:
    _cache.clear()
