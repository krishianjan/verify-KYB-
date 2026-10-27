"""ML layer for risk — COMPLEMENTS the deterministic scorecard, never replaces it.

Why not a pure-ML decision? KYB/AML decisions must be explainable with reason
codes (SR 11-7 model risk, FCRA/ECOA adverse action, EU AI Act). So ML here is
a *signal provider* feeding the auditable scorecard, the way fintechs actually
deploy it:

  * anomaly_check    -> unsupervised IsolationForest over the business
                        population; flags statistical outliers. Zero labels
                        needed, active once there are enough cases.
  * supervised_reject_probability -> logistic regression trained on analyst
                        approve/reject actions as labels (coefficients are
                        explainable). Returns None until enough labels exist.

Every function degrades to a safe default on any error so risk never breaks.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Business,
    Director,
    IdentityAssessment,
    ReviewAction,
    RiskSignal,
    WebIntel,
)

MIN_SAMPLES_ANOMALY = 8
MIN_LABELS_SUPERVISED = 20


def _features(db: Session, business: Business) -> list[float]:
    assessment = db.scalars(
        select(IdentityAssessment)
        .where(IdentityAssessment.business_id == business.id)
        .order_by(IdentityAssessment.created_at.desc())
    ).first()
    intel = db.scalars(
        select(WebIntel)
        .where(WebIntel.business_id == business.id)
        .order_by(WebIntel.created_at.desc())
    ).first()
    officers = len(db.scalars(
        select(Director).where(Director.business_id == business.id)
    ).all())
    sigs = db.scalars(
        select(RiskSignal).where(RiskSignal.business_id == business.id)
    ).all()

    # None confidence = identity not checked; use a neutral 0.5 so the feature
    # vector isn't dragged to the "worst" end by missing data.
    conf = assessment.confidence if (assessment and assessment.confidence is not None) else 0.5
    legit = (intel.legitimacy_score if intel else 50) / 100.0
    age = (intel.domain_age_days if intel and intel.domain_age_days else 0)
    n_high = sum(1 for s in sigs if s.severity == "high")
    n_med = sum(1 for s in sigs if s.severity == "medium")
    return [conf, legit, min(age, 3650) / 3650.0, float(officers), float(n_high), float(n_med)]


def anomaly_check(db: Session, business: Business) -> tuple[bool, float]:
    """(is_anomaly, score). Lower score = more anomalous. Safe no-op if too few."""
    try:
        businesses = db.scalars(select(Business)).all()
        X, target_idx = [], None
        for b in businesses:
            if b.id == business.id:
                target_idx = len(X)
            X.append(_features(db, b))
        if target_idx is None:
            target_idx = len(X)
            X.append(_features(db, business))
        if len(X) < MIN_SAMPLES_ANOMALY:
            return False, 0.0

        import numpy as np
        from sklearn.ensemble import IsolationForest

        arr = np.asarray(X, dtype=float)
        clf = IsolationForest(random_state=42, contamination="auto")
        clf.fit(arr)
        pred = clf.predict(arr)[target_idx]
        score = float(clf.score_samples(arr)[target_idx])
        return bool(pred == -1), score
    except Exception:  # noqa: BLE001
        return False, 0.0


def supervised_reject_probability(db: Session, business: Business) -> float | None:
    """P(reject) from a logistic model trained on analyst actions. None if too few labels."""
    try:
        actions = db.scalars(select(ReviewAction)).all()
        # latest action per business as the label
        label_by_biz: dict[str, int] = {}
        for a in sorted(actions, key=lambda x: x.created_at):
            if a.action in ("approve", "reject"):
                label_by_biz[a.business_id] = 1 if a.action == "reject" else 0
        if len(label_by_biz) < MIN_LABELS_SUPERVISED:
            return None

        import numpy as np
        from sklearn.linear_model import LogisticRegression

        X, y = [], []
        for bid, label in label_by_biz.items():
            b = db.get(Business, bid)
            if b is None:
                continue
            X.append(_features(db, b))
            y.append(label)
        if len(set(y)) < 2:  # need both classes
            return None

        clf = LogisticRegression(max_iter=1000)
        clf.fit(np.asarray(X, dtype=float), np.asarray(y))
        prob = float(clf.predict_proba([_features(db, business)])[0][1])
        return prob
    except Exception:  # noqa: BLE001
        return None
