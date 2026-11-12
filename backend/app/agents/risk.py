"""Risk agent: calibrated, explainable, fairness-audited credit-readiness model.

Trained on a documented synthetic population (no real borrower data). Protected attributes (gender,
social category, region) are NEVER model inputs; they are used only to audit outcomes.
"""
import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

MODEL_VERSION = "artha-risk-1.2.0"
FEATURES = ["months_history", "log_inflow", "inflow_cv", "surplus_ratio", "payers_per_month", "top_payer_share",
            "active_day_ratio", "inflow_trend", "obligation_ratio", "low_month_share", "years_in_operation"]
LABELS = {
    "months_history": "Months of digital transaction history",
    "log_inflow": "Average monthly UPI inflow",
    "inflow_cv": "Month-to-month income volatility",
    "surplus_ratio": "Operating surplus (inflow minus outflow)",
    "payers_per_month": "Distinct paying customers per month",
    "top_payer_share": "Dependence on a single customer",
    "active_day_ratio": "Share of days with sales",
    "inflow_trend": "Revenue trend",
    "obligation_ratio": "Existing EMI / moneylender repayments vs income",
    "low_month_share": "Share of very weak months",
    "years_in_operation": "Years in operation",
}
ACTIONABLE = {
    "months_history": ("Keep routing sales through UPI for {gap:.0f} more months", 12.0),
    "top_payer_share": ("Diversify customers so no single payer exceeds 25% of income", 0.25),
    "obligation_ratio": ("Refinance moneylender debt into a scheme loan to cut repayments", 0.08),
    "surplus_ratio": ("Improve margins (bulk input purchase via SHG / cluster)", 0.25),
    "active_day_ratio": ("Accept UPI on more selling days (QR at stall / doorstep)", 0.75),
}
REGIONS = ["north", "south", "east", "west", "central", "northeast"]
APPROVE_PD = 0.10
TRUE_BETA = {"months_history": -0.06, "log_inflow": -0.5, "inflow_cv": 2.2, "surplus_ratio": -3.0,
             "payers_per_month": -0.008, "top_payer_share": 1.5, "active_day_ratio": -1.2, "inflow_trend": -4.0,
             "obligation_ratio": 3.5, "low_month_share": 1.5, "years_in_operation": -0.04}
CENTER = {"months_history": 12, "log_inflow": 11.0, "inflow_cv": 0.25, "surplus_ratio": 0.22,
          "payers_per_month": 25, "top_payer_share": 0.2, "active_day_ratio": 0.67, "inflow_trend": 0.01,
          "obligation_ratio": 0.13, "low_month_share": 0.1, "years_in_operation": 5}


def synthetic_population(n: int = 24_000, seed: int = 7):
    rng = np.random.default_rng(seed)
    gender = np.where(rng.random(n) < 0.42, "female", "male")
    region = rng.choice(REGIONS, n, p=[0.2, 0.22, 0.18, 0.18, 0.12, 0.10])
    f = gender == "female"
    ne = region == "northeast"
    X = {
        "months_history": np.clip(rng.integers(3, 25, n) - ne * rng.integers(0, 4, n), 3, 24).astype(float),
        "log_inflow": rng.normal(11.0, 0.6, n) - 0.12 * f - 0.08 * ne,
        "inflow_cv": np.clip(rng.lognormal(np.log(0.25), 0.45, n), 0.05, 1.2),
        "surplus_ratio": np.clip(rng.normal(0.22, 0.10, n) + 0.02 * f, -0.3, 0.7),
        "top_payer_share": rng.beta(2, 8, n),
        "active_day_ratio": rng.beta(6, 3, n),
        "inflow_trend": rng.normal(0.01, 0.03, n),
        "obligation_ratio": np.clip(rng.beta(1.5, 10, n) - 0.02 * f, 0, 0.9),
        "years_in_operation": np.clip(rng.gamma(2.0, 3.0, n), 0.3, 30),
    }
    X["payers_per_month"] = np.clip(np.exp(X["log_inflow"] - 11.0) * rng.lognormal(np.log(25), 0.5, n), 2, 300)
    X["low_month_share"] = np.clip(rng.binomial(12, np.clip(X["inflow_cv"] - 0.15, 0.01, 0.9)) / 12, 0, 1)
    logit = -2.55 + sum(TRUE_BETA[k] * (X[k] - CENTER[k]) for k in FEATURES) + rng.normal(0, 0.5, n)
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    M = np.column_stack([X[k] for k in FEATURES])
    return M, y, gender, region


def _ece(p, y, bins=10):
    qs = np.quantile(p, np.linspace(0, 1, bins + 1))
    idx = np.clip(np.searchsorted(qs, p, side="right") - 1, 0, bins - 1)
    rel, ece = [], 0.0
    for b in range(bins):
        m = idx == b
        if m.sum() == 0:
            continue
        mp, oy = float(p[m].mean()), float(y[m].mean())
        rel.append({"bin": b + 1, "predicted": round(mp, 4), "observed": round(oy, 4), "count": int(m.sum())})
        ece += m.mean() * abs(mp - oy)
    return float(ece), rel


class RiskModel:
    def __init__(self):
        M, y, gender, region = synthetic_population()
        rng = np.random.default_rng(11)
        idx = rng.permutation(len(y))
        cut = int(0.7 * len(y))
        tr, te = idx[:cut], idx[cut:]
        self.mu = M[tr].mean(0)
        self.sd = M[tr].std(0) + 1e-9
        Z = (M - self.mu) / self.sd
        self.clf = LogisticRegression(C=1.0, max_iter=1000).fit(Z[tr], y[tr])
        self.boot = []
        for _b in range(25):
            s = rng.choice(tr, len(tr), replace=True)
            m = LogisticRegression(C=1.0, max_iter=500).fit(Z[s], y[s])
            self.boot.append((m.coef_[0], m.intercept_[0]))
        p = self.clf.predict_proba(Z[te])[:, 1]
        yt = y[te]
        ece, rel = _ece(p, yt)
        self.good_median = np.median(M[tr][y[tr] == 0], axis=0)
        self.card = {
            "version": MODEL_VERSION,
            "algorithm": "L2-regularised logistic regression on standardised cash-flow features",
            "training_data": f"{len(tr):,} synthetic MSME cash-flow profiles (documented generator, no real borrowers)",
            "test_size": int(len(te)),
            "features": [{"key": k, "label": LABELS[k], "weight": round(float(w), 3)}
                         for k, w in zip(FEATURES, self.clf.coef_[0], strict=False)],
            "excluded_attributes": ["gender", "social category / caste", "religion", "region / district", "age"],
            "metrics": {"auc": round(float(roc_auc_score(yt, p)), 3), "brier": round(float(brier_score_loss(yt, p)), 4),
                        "ece": round(ece, 4), "base_rate": round(float(yt.mean()), 4)},
            "reliability": rel,
            "approve_threshold_pd": APPROVE_PD,
            "fairness": self._fairness(p, yt, gender[te], region[te]),
            "limitations": [
                "Synthetic training data — must be re-trained and re-validated on real, consented repayment data "
                "before production use.",
                "Score is an input for a human credit officer, never an automatic rejection.",
                "Thin files (< 6 months of history) are flagged as low-confidence.",
            ],
            "monitoring": "Quarterly re-calibration; fairness metrics recomputed on every model release.",
        }

    @staticmethod
    def _group(p, y, mask):
        appr = p <= APPROVE_PD
        good = y == 0
        n = int(mask.sum())
        return {"n": n, "approval_rate": round(float(appr[mask].mean()), 4),
                "tpr_good_borrowers": round(float(appr[mask & good].mean()), 4),
                "mean_predicted_pd": round(float(p[mask].mean()), 4),
                "observed_default": round(float(y[mask].mean()), 4),
                "calibration_gap": round(float(abs(p[mask].mean() - y[mask].mean())), 4)}

    def _fairness(self, p, y, gender, region):
        out = {}
        for name, attr, groups in (("gender", gender, ["female", "male"]), ("region", region, REGIONS)):
            g = {k: self._group(p, y, attr == k) for k in groups}
            rates = [v["approval_rate"] for v in g.values()]
            tprs = [v["tpr_good_borrowers"] for v in g.values()]
            di = min(rates) / max(rates) if max(rates) else 1.0
            eo = max(tprs) - min(tprs)
            cal = max(v["calibration_gap"] for v in g.values())
            out[name] = {"groups": g, "disparate_impact": round(di, 3), "equal_opportunity_gap": round(eo, 3),
                         "max_calibration_gap": round(cal, 4),
                         "checks": {"disparate_impact_>=_0.8": di >= 0.8, "equal_opportunity_gap_<=_0.10": eo <= 0.10,
                                    "calibration_gap_<=_0.03": cal <= 0.03}}
        return out

    def _vec(self, feats: dict) -> np.ndarray:
        return np.array([float(feats.get(k, self.mu[i])) for i, k in enumerate(FEATURES)])

    def _pd(self, x: np.ndarray) -> float:
        return float(self.clf.predict_proba(((x - self.mu) / self.sd).reshape(1, -1))[0, 1])

    @staticmethod
    def score(pd: float) -> int:
        odds = (1 - pd) / max(pd, 1e-6)
        return int(max(300, min(900, round(700 + (50 / math.log(2)) * math.log(odds / 19)))))

    @staticmethod
    def band(score: int) -> str:
        return "A" if score >= 750 else "B" if score >= 700 else "C" if score >= 640 else "D" if score >= 580 else "E"

    def assess(self, feats: dict) -> dict:
        x = self._vec(feats)
        z = (x - self.mu) / self.sd
        pd = self._pd(x)
        boots = [1 / (1 + math.exp(-(float(np.dot(c, z)) + i))) for c, i in self.boot]
        lo, hi = float(np.percentile(boots, 5)), float(np.percentile(boots, 95))
        thin = x[0] < 6
        if thin:
            lo, hi = max(0.0, lo * 0.6), min(1.0, hi * 1.6)
        contrib = self.clf.coef_[0] * z
        factors = sorted(({"feature": k, "label": LABELS[k], "value": round(float(x[i]), 4),
                           "impact": round(float(contrib[i]), 4),
                           "direction": "raises risk" if contrib[i] > 0 else "lowers risk"}
                          for i, k in enumerate(FEATURES)), key=lambda f: -abs(f["impact"]))
        suggestions = []
        for f in [f for f in factors if f["impact"] > 0 and f["feature"] in ACTIONABLE][:3]:
            i = FEATURES.index(f["feature"])
            text, target = ACTIONABLE[f["feature"]]
            x2 = x.copy()
            x2[i] = target if f["feature"] != "months_history" else max(x[i] + 6, target)
            pd2 = self._pd(x2)
            if pd2 < pd:
                suggestions.append({"action": text.format(gap=max(0, x2[i] - x[i])), "feature": f["feature"],
                                    "new_pd": round(pd2, 4), "new_score": self.score(pd2)})
        s = self.score(pd)
        return {
            "model_version": MODEL_VERSION, "pd": round(pd, 4), "pd_interval_90": [round(lo, 4), round(hi, 4)],
            "score": s, "band": self.band(s), "credit_ready": pd <= APPROVE_PD,
            "confidence": "low (thin file)" if thin else ("medium" if hi - lo > 0.06 else "high"),
            "factors": factors, "reason_codes": [f["label"] for f in factors if f["impact"] > 0][:4],
            "strengths": [f["label"] for f in factors if f["impact"] < 0][:4], "suggestions": suggestions,
            "protected_attributes_used": False,
            "note": "Indicative credit-readiness estimate to support — never replace — a lender's decision.",
        }


_MODEL: RiskModel | None = None


def model() -> RiskModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = RiskModel()
    return _MODEL
