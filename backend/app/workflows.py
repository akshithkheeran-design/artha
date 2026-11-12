import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import audit, consent
from .agents import applications as appl
from .agents.schemes import SCHEME_INDEX
from .crypto import canonical, decrypt_json, encrypt_json, sha256_hex, sign
from .models import Application, Business, User, utcnow
from .services import context
from .vault import owner_dek

LENDERS = [
    {"org": "Navodaya Bank · Tiruppur Branch", "type": "lender", "kind": "Public sector bank"},
    {"org": "Kaveri Gramin Bank", "type": "lender", "kind": "Regional rural bank"},
    {"org": "Pragati Small Finance Bank", "type": "lender", "kind": "Small finance bank"},
    {"org": "Sahyog Finance NBFC", "type": "lender", "kind": "NBFC"},
    {"org": "District Industries Centre · PMEGP Cell", "type": "dic", "kind": "DIC / scheme agency"},
]
LENDER_INDEX = {l["org"]: l for l in LENDERS}
DEFAULT_SHARE = ["profile", "cashflow_summary", "risk_report", "eligibility", "documents"]


def snapshot_for(db: Session, business: Business, scheme_id: str, amount: int, lender_org: str) -> dict:
    ctx = context(db, business, scheme_id)
    sr = next(e for e in ctx["eligibility"] if e["scheme_id"] == scheme_id)
    return appl.build_snapshot(business, ctx["profile"], sr, ctx["cash"], ctx["risk"], ctx["documents"], amount,
                               lender_org)


def create(db: Session, actor: User, business: Business, scheme_id: str, lender_org: str, amount: int) -> Application:
    if scheme_id not in SCHEME_INDEX:
        raise HTTPException(422, "Unknown scheme")
    if lender_org not in LENDER_INDEX:
        raise HTTPException(422, "Unknown lender / agency")
    if scheme_id == "pmegp" and LENDER_INDEX[lender_org]["type"] != "dic":
        raise HTTPException(422, "PMEGP applications are routed through the DIC / KVIC agency")
    if not 1_000 <= amount <= SCHEME_INDEX[scheme_id]["max_amount"]:
        raise HTTPException(422, "Amount outside the scheme's range")
    snap = snapshot_for(db, business, scheme_id, amount, lender_org)
    if snap["scheme"]["status"] == "ineligible":
        raise HTTPException(422, "The Scheme Navigator found this scheme is not applicable — see the cited rule")
    a = Application(ref=f"ART-{secrets.randbelow(900000) + 100000}", business_id=business.id, scheme_id=scheme_id,
                    lender_org=lender_org, amount=amount, status="awaiting_owner_approval",
                    completeness=appl.completeness(snap), created_by=actor.id,
                    timeline=[appl.event("awaiting_owner_approval",
                                         f"Drafted by {'owner' if actor.id == business.owner_id else actor.role}", actor.role)])
    a.snapshot_enc = encrypt_json(owner_dek(business), snap, f"app:{business.id}:{a.ref}")
    db.add(a)
    db.flush()
    audit.record(db, actor, "application.drafted", business.id,
                 {"application": a.ref, "scheme": scheme_id, "lender_org": lender_org, "amount": amount})
    return a


def read_snapshot(business: Business, a: Application) -> dict:
    return decrypt_json(owner_dek(business), a.snapshot_enc, f"app:{business.id}:{a.ref}")


def approve(db: Session, owner: User, business: Business, a: Application, scopes: list[str], days: int) -> Application:
    if a.status != "awaiting_owner_approval":
        raise HTTPException(409, "Application is not awaiting your approval")
    snap = snapshot_for(db, business, a.scheme_id, a.amount, a.lender_org)
    a.snapshot_enc = encrypt_json(owner_dek(business), snap, f"app:{business.id}:{a.ref}")
    a.completeness = appl.completeness(snap)
    a.snapshot_hash = sha256_hex(canonical({"ref": a.ref, "snapshot": snap}))
    a.approval_signature = sign(a.snapshot_hash.encode())
    a.approved_at = utcnow()
    lender = LENDER_INDEX[a.lender_org]
    c = consent.grant(db, owner, business, lender["type"], a.lender_org, "credit_assessment", scopes, days,
                      commit=False)
    a.consent_id = c.id
    a.status = "submitted"
    a.updated_at = utcnow()
    a.timeline = a.timeline + [appl.event("submitted", f"Approved by owner · consent #{c.id} · file hash "
                                                       f"{a.snapshot_hash[:12]}…", "entrepreneur")]
    audit.record(db, owner, "application.owner_approved", business.id,
                 {"application": a.ref, "snapshot_hash": a.snapshot_hash, "consent_id": c.id, "scopes": scopes})
    return a
