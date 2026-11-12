"""Purpose-bound, time-limited, revocable consent artefacts (DEPA / Account Aggregator style)."""
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import audit
from .crypto import canonical, sha256_hex, sign
from .models import Application, Business, Consent, User, utcnow

PURPOSES = {
    "cashflow_analysis": "Analyse my UPI / bank cash-flows to build a credit-readiness profile",
    "eligibility_check": "Check which government schemes I qualify for",
    "assisted_onboarding": "Let a business correspondent help me prepare my file",
    "credit_assessment": "Let a lender / scheme agency assess my loan application",
}
SCOPES = {
    "profile": "Business profile (masked identifiers)",
    "cashflow_summary": "Monthly cash-flow summary and indicators",
    "upi_transactions": "Raw UPI transaction lines (counterparties pseudonymised)",
    "risk_report": "Credit-readiness score and its explanation",
    "eligibility": "Scheme eligibility results with citations",
    "documents": "Uploaded / fetched documents",
}
GRANTEE_TYPES = {"platform", "agent", "lender", "dic"}
PLATFORM_ORG = "ARTHA Platform (analysis agents)"


def _artefact(c: Consent) -> dict:
    return {"business_id": c.business_id, "grantee_type": c.grantee_type, "grantee_org": c.grantee_org,
            "purpose": c.purpose, "scopes": sorted(c.scopes), "granted_at": c.granted_at.isoformat(),
            "expires_at": c.expires_at.isoformat()}


def grant(db: Session, actor: User, business: Business, grantee_type: str, grantee_org: str, purpose: str,
          scopes: list[str], days: int, commit: bool = True) -> Consent:
    if grantee_type not in GRANTEE_TYPES or purpose not in PURPOSES:
        raise HTTPException(422, "Unknown grantee type or purpose")
    bad = set(scopes) - set(SCOPES)
    if bad or not scopes:
        raise HTTPException(422, f"Invalid scopes: {sorted(bad) or 'none given'}")
    if not 1 <= days <= 365:
        raise HTTPException(422, "Consent validity must be between 1 and 365 days")
    now = utcnow()
    c = Consent(business_id=business.id, grantee_type=grantee_type, grantee_org=grantee_org, purpose=purpose,
                scopes=sorted(set(scopes)), status="active", granted_at=now, expires_at=now + timedelta(days=days))
    c.artefact_hash = sha256_hex(canonical(_artefact(c)))
    c.signature = sign(c.artefact_hash.encode())
    db.add(c)
    db.flush()
    audit.record(db, actor, "consent.granted", business.id,
                 {"consent_id": c.id, "grantee_type": grantee_type, "grantee_org": grantee_org,
                  "purpose": purpose, "scopes": c.scopes, "days": days, "artefact_hash": c.artefact_hash},
                 commit=commit)
    return c


def revoke(db: Session, actor: User, c: Consent) -> Consent:
    if c.status != "active":
        raise HTTPException(409, "Consent is not active")
    c.status = "revoked"
    c.revoked_at = utcnow()
    audit.record(db, actor, "consent.revoked", c.business_id, {"consent_id": c.id, "grantee_org": c.grantee_org})
    return c


def refresh_status(c: Consent) -> Consent:
    if c.status == "active" and c.expires_at <= utcnow():
        c.status = "expired"
    return c


def find_active(db: Session, business_id: int, grantee_type: str, grantee_org: str | None, scope: str,
                purpose: str | None = None) -> Consent | None:
    q = db.query(Consent).filter(Consent.business_id == business_id, Consent.grantee_type == grantee_type,
                                 Consent.status == "active")
    if grantee_org is not None:
        q = q.filter(Consent.grantee_org == grantee_org)
    if purpose:
        q = q.filter(Consent.purpose == purpose)
    for c in q.order_by(Consent.id.desc()).all():
        refresh_status(c)
        if c.status == "active" and scope in (c.scopes or []):
            return c
    return None


def authorize(db: Session, user: User, business: Business, scope: str, log: bool = True) -> Consent | None:
    """Return the consent that authorises `user` to read `scope` of `business` (None for the owner)."""
    if user.role == "entrepreneur":
        if business.owner_id != user.id:
            raise HTTPException(404, "Business not found")
        return None
    if user.role == "agent":
        c = find_active(db, business.id, "agent", user.org, scope, "assisted_onboarding")
    elif user.role in ("lender", "dic"):
        c = find_active(db, business.id, user.role, user.org, scope, "credit_assessment")
    else:
        c = None
    if not c:
        raise HTTPException(403, f"No active consent from the owner covers '{scope}' for your organisation")
    if log:
        audit.record(db, user, "data.accessed", business.id,
                     {"scope": scope, "purpose": c.purpose, "consent_id": c.id, "org": user.org})
    return c


def platform_consent(db: Session, business: Business, scope: str) -> Consent:
    c = find_active(db, business.id, "platform", PLATFORM_ORG, scope)
    if not c:
        raise HTTPException(403, f"The owner has not consented to platform analysis of '{scope}'. "
                                 "Grant it from the Consent Vault first.")
    return c


def visible_business_ids(db: Session, user: User) -> list[int]:
    if user.role == "entrepreneur":
        return [b.id for b in db.query(Business).filter(Business.owner_id == user.id).all()]
    gtype = {"agent": "agent", "lender": "lender", "dic": "dic"}.get(user.role)
    if not gtype:
        return []
    ids = set()
    for c in db.query(Consent).filter(Consent.grantee_type == gtype, Consent.grantee_org == user.org,
                                      Consent.status == "active").all():
        if refresh_status(c).status == "active":
            ids.add(c.business_id)
    if gtype in ("lender", "dic"):
        ids |= {a.business_id for a in db.query(Application).filter(Application.lender_org == user.org,
                                                                     Application.status != "draft").all()}
    return sorted(ids)
