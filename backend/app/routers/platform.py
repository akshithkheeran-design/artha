from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import audit, consent
from ..agents import applications as appl
from ..agents.risk import model
from ..agents.schemes import DOCUMENTS, SCHEMES
from ..crypto import public_key_b64
from ..db import get_db
from ..models import Application, AuditLog, Business, CashflowDataset, Consent, Document, FieldInterview, User, utcnow
from ..security import current_user, redact, require_roles, verify_password
from ..services import context, transactions
from ..vault import read_profile

router = APIRouter(prefix="/api", tags=["platform"])


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/schemes")
def schemes():
    return {"schemes": SCHEMES, "documents": DOCUMENTS}


@router.get("/model/card")
def model_card(user: User = Depends(current_user)):
    return model().card


@router.get("/analytics/overview")
def overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    businesses = db.query(Business).filter(Business.shredded.is_(False)).all()
    apps = db.query(Application).all()
    elig_total, ready, scores, savings, docs_req, districts, sectors = 0, 0, [], 0, [], {}, Counter()
    funnel = Counter()
    for b in businesses:
        ctx = context(db, b)
        e = [x for x in ctx["eligibility"] if x["status"] == "eligible"]
        elig_total += len(e)
        funnel["onboarded"] += 1
        if ctx["cash"]:
            funnel["consented_data"] += 1
            savings += ctx["cash"]["summary"]["annual_interest_saving"]
        if e:
            funnel["eligible"] += 1
        if ctx["risk"]:
            scores.append(ctx["risk"]["score"])
            ready += ctx["risk"]["credit_ready"]
        docs_req.append(ctx["documents"]["stats"]["required"])
        sectors[b.sector] += 1
        d = districts.setdefault(b.district, {"district": b.district, "state": b.state, "lat": b.lat, "lng": b.lng,
                                              "count": 0, "eligible": 0, "sectors": Counter()})
        d["count"] += 1
        d["eligible"] += len(e)
        d["sectors"][b.sector] += 1
    status = Counter(a.status for a in apps)
    applied = {a.business_id for a in apps}
    approved = {a.business_id for a in apps if a.approved_at}
    sanctioned_amt = sum(a.amount for a in apps if a.status == "sanctioned")
    pipeline_amt = sum(a.amount for a in apps if a.approved_at)
    funnel.update({"applied": len(applied), "owner_approved": len(approved),
                   "sanctioned": len({a.business_id for a in apps if a.status == "sanctioned"})})
    stalled = [a for a in apps if (appl.stall_info(a) or {}).get("stalled")]
    feed = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(14).all()
    n = max(len(businesses), 1)
    return {
        "kpis": {"businesses": len(businesses), "schemes_matched": elig_total,
                 "avg_schemes_per_business": round(elig_total / n, 2),
                 "credit_ready_share": round(ready / max(len(scores), 1), 3),
                 "avg_score": round(sum(scores) / max(len(scores), 1)),
                 "avg_documents": round(sum(docs_req) / n, 1), "traditional_documents": 18,
                 "applications": len(apps), "stalled": len(stalled), "sanctioned_amount": sanctioned_amt,
                 "middleman_fees_avoided": round(pipeline_amt * 0.125),
                 "annual_interest_saving": savings,
                 "avg_completeness": round(sum(a.completeness for a in apps) / max(len(apps), 1), 3),
                 "consents_active": db.query(Consent).filter(Consent.status == "active").count()},
        "funnel": [{"stage": k, "count": funnel[k]} for k in
                   ("onboarded", "consented_data", "eligible", "applied", "owner_approved", "sanctioned")],
        "status": [{"status": k, "count": v} for k, v in status.items()],
        "sectors": [{"sector": k, "count": v} for k, v in sectors.most_common()],
        "districts": [{**d, "sectors": dict(d["sectors"])} for d in districts.values()],
        "score_distribution": [{"band": bnd, "count": sum(1 for s in scores if model().band(s) == bnd)}
                               for bnd in "ABCDE"],
        "feed": [{"ts": f.ts, "action": f.action, "role": f.actor_role, "hash": f.hash[:12]} for f in feed],
    }


@router.get("/analytics/money-trail")
def money_trail(files_per_month: int = Query(120, ge=1, le=100000),
                incomplete_share: float = Query(0.45, ge=0, le=1),
                followup_hours: float = Query(6, ge=0, le=200), officer_cost_per_hour: float = Query(650, ge=0, le=100000),
                dropout_share: float = Query(0.35, ge=0, le=1), avg_loan: float = Query(300000, ge=1000, le=1e8),
                net_interest_margin: float = Query(0.035, ge=0, le=0.3),
                acquisition_cost: float = Query(2500, ge=0, le=1e6), extra_days: float = Query(38, ge=0, le=365),
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    inc = files_per_month * incomplete_share
    staff = inc * followup_hours * officer_cost_per_hour
    dropouts = inc * dropout_share
    lost_margin = dropouts * avg_loan * net_interest_margin
    sunk = dropouts * acquisition_cost
    per_file = followup_hours * officer_cost_per_hour + dropout_share * (avg_loan * net_interest_margin + acquisition_cost)
    submitted = [a for a in db.query(Application).all() if a.approved_at]
    measured_incomplete = (sum(a.completeness < 0.9 for a in submitted) / len(submitted)) if submitted else incomplete_share
    docs_req = sum(1 for a in submitted for t in a.timeline if t["status"] == "docs_requested")
    with_inc = files_per_month * measured_incomplete
    with_staff = with_inc * followup_hours * 0.3 * officer_cost_per_hour
    with_drop = with_inc * dropout_share * 0.5
    with_total = with_staff + with_drop * (avg_loan * net_interest_margin + acquisition_cost)
    base_total = staff + lost_margin + sunk
    return {
        "assumptions_note": "Defaults are placeholders — replace with figures gathered from branch managers in the field.",
        "lender": {"incomplete_files": round(inc, 1), "staff_cost": round(staff), "dropouts": round(dropouts, 1),
                   "lost_margin": round(lost_margin), "sunk_acquisition": round(sunk),
                   "cost_per_incomplete_file": round(per_file), "monthly_total": round(base_total),
                   "annual_total": round(base_total * 12), "capital_idle_days": extra_days},
        "with_artha": {"measured_incomplete_share": round(measured_incomplete, 3), "monthly_total": round(with_total),
                       "monthly_saving": round(base_total - with_total), "docs_requests_observed": docs_req,
                       "files_observed": len(submitted)},
        "borrower": {"loan": avg_loan, "moneylender_interest": round(avg_loan * 0.30),
                     "scheme_interest": round(avg_loan * 0.11), "agent_fee": round(avg_loan * 0.125),
                     "annual_saving": round(avg_loan * 0.19 + avg_loan * 0.125)},
    }


class InterviewIn(BaseModel):
    respondent_type: str = Field(pattern=r"^(entrepreneur|shg|branch_manager|bc_agent|dic_officer)$")
    sector: str = Field(max_length=40, pattern=r"^[\w ]+$")
    state: str = Field(max_length=60, pattern=r"^[\w ]+$")
    schemes_heard: list[str] = Field(default_factory=list, max_length=10)
    heard_from: str = Field("none", max_length=30)
    last_loan_documents: int | None = Field(None, ge=0, le=60)
    stalled_at: str = Field("none", max_length=30)
    agent_fee_pct: float | None = Field(None, ge=0, le=50)
    agent_services: list[str] = Field(default_factory=list, max_length=10)
    informal_records: list[str] = Field(default_factory=list, max_length=10)
    willing_to_share: str = Field("conditional", pattern=r"^(yes|no|conditional)$")
    branch_needs: list[str] = Field(default_factory=list, max_length=10)
    dropout_reason: str = Field("none", max_length=40)
    cost_per_incomplete_file: float | None = Field(None, ge=0, le=1e6)
    notes: str = Field("", max_length=600)


@router.get("/field/interviews")
def interviews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": i.id, "respondent_type": i.respondent_type, "sector": i.sector, "state": i.state,
             "answers": i.answers, "is_sample": i.is_sample, "created_at": i.created_at.isoformat()}
            for i in db.query(FieldInterview).order_by(FieldInterview.id.desc()).all()]


@router.post("/field/interviews")
def add_interview(body: InterviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = body.model_dump()
    data["notes"], found = redact(data["notes"])
    i = FieldInterview(interviewer_id=user.id, respondent_type=body.respondent_type, sector=body.sector,
                       state=body.state, answers={k: v for k, v in data.items()
                                                  if k not in ("respondent_type", "sector", "state")})
    db.add(i)
    audit.record(db, user, "field.interview_added", None, {"respondent_type": body.respondent_type, "pii_redacted": found})
    return {"id": i.id, "redacted": found}


@router.get("/field/insights")
def field_insights(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(FieldInterview).all()
    c = {k: Counter() for k in ("schemes_heard", "heard_from", "stalled_at", "agent_services", "informal_records",
                                 "willing_to_share", "branch_needs", "dropout_reason")}
    fees, docs, costs = [], [], []
    for r in rows:
        a = r.answers
        for k in c:
            v = a.get(k)
            for item in (v if isinstance(v, list) else [v]):
                if item and item != "none":
                    c[k][item] += 1
        if a.get("agent_fee_pct") is not None:
            fees.append(a["agent_fee_pct"])
        if a.get("last_loan_documents") is not None:
            docs.append(a["last_loan_documents"])
        if a.get("cost_per_incomplete_file") is not None:
            costs.append(a["cost_per_incomplete_file"])
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    return {"respondents": len(rows), "by_type": dict(Counter(r.respondent_type for r in rows)),
            "avg_agent_fee_pct": avg(fees), "avg_documents_last_loan": avg(docs),
            "avg_cost_per_incomplete_file": avg(costs),
            **{k: [{"label": lbl, "count": n} for lbl, n in v.most_common()] for k, v in c.items()}}


@router.get("/audit")
def audit_list(limit: int = Query(150, ge=1, le=500), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    if user.role == "entrepreneur":
        ids = consent.visible_business_ids(db, user)
        q = q.filter((AuditLog.business_id.in_(ids or [-1])) | (AuditLog.actor_id == user.id))
    elif user.role != "auditor":
        q = q.filter(AuditLog.actor_id == user.id)
    return [{"id": r.id, "ts": r.ts, "actor_role": r.actor_role, "action": r.action, "business_id": r.business_id,
             "details": r.details, "prev_hash": r.prev_hash, "hash": r.hash, "signature": r.signature}
            for r in q.order_by(AuditLog.id.desc()).limit(limit).all()]


@router.get("/audit/verify")
def audit_verify(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {**audit.verify_chain(db), "public_key_ed25519": public_key_b64(), "algorithm": "SHA-256 chain + Ed25519"}


@router.get("/me/export")
def export(user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    out = []
    for b in db.query(Business).filter(Business.owner_id == user.id, Business.shredded.is_(False)).all():
        tx = transactions(db, b) or []
        out.append({"business": {"name": b.name, "sector": b.sector, "district": b.district, "state": b.state},
                    "profile": read_profile(b), "transactions": len(tx),
                    "consents": [{"id": c.id, "grantee": c.grantee_org, "purpose": c.purpose, "scopes": c.scopes,
                                  "status": c.status} for c in db.query(Consent).filter(Consent.business_id == b.id)],
                    "documents": [d.doc_type for d in db.query(Document).filter(Document.business_id == b.id)]})
    audit.record(db, user, "privacy.data_exported", None, {})
    return {"exported_at": utcnow().isoformat(), "data": out}


class EraseIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirm_text: str


@router.post("/me/erase")
def erase(body: EraseIn, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    if body.confirm_text != "ERASE" or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Type ERASE and your correct password to confirm")
    for b in db.query(Business).filter(Business.owner_id == user.id).all():
        for c in db.query(Consent).filter(Consent.business_id == b.id, Consent.status == "active"):
            c.status, c.revoked_at = "revoked", utcnow()
        for a in db.query(Application).filter(Application.business_id == b.id):
            if a.status not in ("sanctioned", "rejected"):
                a.status = "withdrawn"
            a.snapshot_enc = None
        db.query(CashflowDataset).filter(CashflowDataset.business_id == b.id).delete()
        db.query(Document).filter(Document.business_id == b.id).delete()
        b.profile_enc, b.shredded = None, True
        audit.record(db, user, "privacy.crypto_shredded", b.id, {}, commit=False)
    user.dek_wrapped = None
    user.token_version += 1
    db.commit()
    return {"ok": True, "message": "Your encryption key was destroyed; your data can no longer be read by anyone."}
