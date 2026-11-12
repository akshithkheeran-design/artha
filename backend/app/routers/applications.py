from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import audit, consent, workflows
from ..agents import applications as appl
from ..agents.schemes import SCHEME_INDEX
from ..db import get_db
from ..models import Application, Business, Consent, User, utcnow
from ..security import current_user, require_roles, verify_password
from .deps import get_business

router = APIRouter(prefix="/api", tags=["applications"])
HIDDEN_FROM_LENDER = {"draft", "awaiting_owner_approval"}


def out(a: Application, b: Business) -> dict:
    return {"id": a.id, "ref": a.ref, "business_id": a.business_id, "business_name": b.name, "district": b.district,
            "sector": b.sector, "scheme_id": a.scheme_id, "scheme": SCHEME_INDEX[a.scheme_id]["short"],
            "lender_org": a.lender_org, "amount": a.amount, "status": a.status, "completeness": a.completeness,
            "created_at": a.created_at.isoformat(), "updated_at": a.updated_at.isoformat(),
            "approved_at": a.approved_at.isoformat() if a.approved_at else None, "snapshot_hash": a.snapshot_hash,
            "approval_signature": a.approval_signature, "decision_reason": a.decision_reason,
            "decision_reason_text": appl.REASON_CODES.get(a.decision_reason or ""), "timeline": a.timeline,
            "stall": appl.stall_info(a), "consent_id": a.consent_id}


def _can_view(db: Session, user: User, a: Application, b: Business) -> Consent | None:
    if user.role == "entrepreneur":
        if b.owner_id != user.id:
            raise HTTPException(404, "Application not found")
        return None
    if user.role == "agent":
        return consent.authorize(db, user, b, "profile", log=False)
    if user.role in ("lender", "dic"):
        if a.lender_org != user.org or a.status in HIDDEN_FROM_LENDER:
            raise HTTPException(404, "Application not found")
        c = db.get(Consent, a.consent_id) if a.consent_id else None
        if not c or consent.refresh_status(c).status != "active":
            raise HTTPException(403, "The applicant's consent for this file is no longer active")
        return c
    raise HTTPException(403, "Not permitted")


@router.get("/applications")
def list_applications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Application, Business).join(Business, Business.id == Application.business_id)
    if user.role == "entrepreneur":
        q = q.filter(Business.owner_id == user.id)
    elif user.role == "agent":
        q = q.filter(Application.business_id.in_(consent.visible_business_ids(db, user) or [-1]))
    elif user.role in ("lender", "dic"):
        q = q.filter(Application.lender_org == user.org, Application.status.notin_(HIDDEN_FROM_LENDER))
    else:
        raise HTTPException(403, "Not permitted")
    return [out(a, b) for a, b in q.order_by(Application.updated_at.desc()).all()]


class DraftIn(BaseModel):
    scheme_id: str = Field(max_length=40)
    lender_org: str = Field(max_length=160)
    amount: int = Field(ge=1000, le=100_000_000)


@router.post("/businesses/{business_id}/applications")
def draft_application(business_id: int, body: DraftIn, user: User = Depends(require_roles("entrepreneur", "agent")),
                      db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile", log=False)
    a = workflows.create(db, user, b, body.scheme_id, body.lender_org, body.amount)
    db.commit()
    return out(a, b)


@router.get("/applications/{app_id}")
def get_application(app_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    b = get_business(db, a.business_id)
    c = _can_view(db, user, a, b)
    snap = workflows.read_snapshot(b, a)
    if c is not None and user.role in ("lender", "dic"):
        scopes = set(c.scopes)
        if "cashflow_summary" not in scopes:
            snap["cashflow"] = None
        if "risk_report" not in scopes:
            snap["risk"] = None
        if "documents" not in scopes:
            snap["documents"] = []
        if "profile" not in scopes:
            snap["applicant"] = {"business_name": b.name, "district": b.district}
        audit.record(db, user, "data.accessed", b.id, {"scope": "application_file", "application": a.ref,
                                                        "consent_id": c.id, "org": user.org})
    return {**out(a, b), "snapshot": snap, "shared_scopes": c.scopes if c else None,
            "nudge": appl.DROP_OUT_NUDGES.get(a.status)}


class ApproveIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirm: bool
    scopes: list[str] = Field(default_factory=lambda: list(workflows.DEFAULT_SHARE), min_length=1)
    days: int = Field(90, ge=7, le=365)


@router.post("/applications/{app_id}/approve")
def approve_application(app_id: int, body: ApproveIn, user: User = Depends(require_roles("entrepreneur")),
                        db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    b = get_business(db, a.business_id)
    if b.owner_id != user.id:
        raise HTTPException(404, "Application not found")
    if not body.confirm:
        raise HTTPException(422, "Please confirm you have reviewed the application")
    if not verify_password(body.password, user.password_hash):
        audit.record(db, user, "application.approval_failed", b.id, {"application": a.ref})
        raise HTTPException(401, "Password incorrect — approval not recorded")
    workflows.approve(db, user, b, a, body.scopes, body.days)
    db.commit()
    return out(a, b)


@router.post("/applications/{app_id}/withdraw")
def withdraw(app_id: int, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    b = get_business(db, a.business_id)
    if b.owner_id != user.id:
        raise HTTPException(404, "Application not found")
    if a.status in ("sanctioned", "rejected", "withdrawn"):
        raise HTTPException(409, "Application already closed")
    a.status = "withdrawn"
    a.updated_at = utcnow()
    a.timeline = a.timeline + [appl.event("withdrawn", "Withdrawn by owner", "entrepreneur")]
    if a.consent_id:
        c = db.get(Consent, a.consent_id)
        if c and c.status == "active":
            consent.revoke(db, user, c)
    audit.record(db, user, "application.withdrawn", b.id, {"application": a.ref})
    return out(a, b)


class DecisionIn(BaseModel):
    action: str = Field(pattern=r"^(under_review|docs_requested|sanctioned|rejected)$")
    reason_code: str | None = Field(None, pattern=r"^R0[1-6]$")
    note: str = Field("", max_length=300)


@router.post("/applications/{app_id}/decision")
def decide(app_id: int, body: DecisionIn, user: User = Depends(require_roles("lender", "dic")),
           db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    b = get_business(db, a.business_id)
    _can_view(db, user, a, b)
    if a.status in ("sanctioned", "rejected", "withdrawn"):
        raise HTTPException(409, "Application already closed")
    if body.action == "rejected" and not body.reason_code:
        raise HTTPException(422, "A rejection must cite a reason code so the applicant knows what to fix")
    a.status = body.action
    a.decision_reason = body.reason_code
    a.updated_at = utcnow()
    note = body.note.strip() or (appl.REASON_CODES.get(body.reason_code or "") or body.action.replace("_", " ").title())
    a.timeline = a.timeline + [appl.event(body.action, note, user.org or user.role)]
    audit.record(db, user, f"application.{body.action}", b.id,
                 {"application": a.ref, "reason_code": body.reason_code, "org": user.org})
    return out(a, b)


@router.get("/applications-meta")
def meta(user: User = Depends(current_user)):
    return {"reason_codes": appl.REASON_CODES, "lenders": workflows.LENDERS, "share_default": workflows.DEFAULT_SHARE}
