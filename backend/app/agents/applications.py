"""Application agent: assembles a lender-ready file. Only the owner can approve submission."""
from datetime import timedelta

from ..models import utcnow

STATUS_FLOW = ["draft", "awaiting_owner_approval", "submitted", "under_review", "docs_requested", "sanctioned",
               "rejected", "withdrawn"]
DECISIONS = {"under_review", "docs_requested", "sanctioned", "rejected"}
REASON_CODES = {
    "R01": "Insufficient digital transaction history",
    "R02": "Existing repayment obligations too high for requested amount",
    "R03": "Documents incomplete after follow-up",
    "R04": "Outside scheme eligibility rules",
    "R05": "Project viability concerns (please discuss with branch)",
    "R06": "KYC mismatch — re-verify identity",
}
STALL_DAYS = {"submitted": 7, "under_review": 14, "docs_requested": 10, "awaiting_owner_approval": 5}
DROP_OUT_NUDGES = {
    "awaiting_owner_approval": "Review the file and approve with your password — nothing is sent without you.",
    "docs_requested": "The branch asked for documents — upload from your phone, ARTHA shows exactly which.",
    "submitted": "ARTHA has pinged the branch; applications are usually picked up within 7 days.",
    "under_review": "Under review — ARTHA will escalate to the scheme nodal officer if no update in 14 days.",
}


def masked_profile(business, profile: dict) -> dict:
    def m(v, keep=4):
        return ("•" * max(0, len(str(v)) - keep) + str(v)[-keep:]) if v else None
    return {"business_name": business.name, "sector": business.sector, "activity_type": business.activity_type,
            "district": business.district, "state": business.state, "area": business.area,
            "years_in_operation": business.years_in_operation, "employees": business.employees,
            "owner_name": profile.get("owner_name"), "pan": m(profile.get("pan")),
            "udyam_number": m(profile.get("udyam_number"), 7), "phone": m(profile.get("phone")),
            "aadhaar": ("XXXX-XXXX-" + profile["aadhaar_last4"]) if profile.get("aadhaar_last4") else None}


def build_snapshot(business, profile, scheme_result, cash, risk, docs, amount, lender_org) -> dict:
    return {"applicant": masked_profile(business, profile), "scheme": {k: scheme_result[k] for k in (
                "scheme_id", "name", "status", "indicative_amount", "note", "checks", "citations")},
            "amount": amount, "lender_org": lender_org, "purpose": business.loan_purpose,
            "cashflow": cash["summary"] if cash else None, "risk": {k: risk[k] for k in (
                "model_version", "pd", "pd_interval_90", "score", "band", "confidence", "reason_codes",
                "strengths", "factors")} if risk else None,
            "documents": docs["items"], "completeness": docs["stats"]["completeness"]}


def completeness(snapshot: dict) -> float:
    doc = snapshot.get("completeness", 0)
    parts = [doc, 1.0 if snapshot.get("cashflow") else 0.0, 1.0 if snapshot.get("risk") else 0.0,
             1.0 if snapshot["scheme"]["status"] == "eligible" else 0.5]
    return round(0.55 * parts[0] + 0.2 * parts[1] + 0.15 * parts[2] + 0.1 * parts[3], 3)


def stall_info(app) -> dict | None:
    limit = STALL_DAYS.get(app.status)
    if not limit:
        return None
    days = (utcnow() - app.updated_at).days
    return {"days_in_status": days, "limit": limit, "stalled": days >= limit,
            "nudge": DROP_OUT_NUDGES.get(app.status)} if days >= 0 else None


def event(status: str, note: str, actor: str, at=None) -> dict:
    return {"status": status, "note": note, "actor": actor, "at": (at or utcnow()).isoformat()}


def days_ago(n: float):
    return utcnow() - timedelta(days=n)
