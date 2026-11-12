import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import audit, consent
from ..agents import cashflow, intake, orchestrator
from ..agents.applications import masked_profile
from ..agents.risk import model
from ..config import MAX_UPLOAD_BYTES
from ..crypto import decrypt_bytes, encrypt_bytes, encrypt_json, new_wrapped_dek, sha256_hex
from ..db import get_db
from ..models import AuditLog, Business, CashflowDataset, Consent, Document, User
from ..security import current_user, require_roles
from ..services import context, latest_dataset, transactions
from ..vault import owner_dek, read_profile, write_profile
from .deps import get_business

router = APIRouter(prefix="/api", tags=["business"])

REGION_OF = {
    "Punjab": "north", "Haryana": "north", "Delhi": "north", "Himachal Pradesh": "north", "Uttarakhand": "north",
    "Jammu And Kashmir": "north", "Uttar Pradesh": "central", "Madhya Pradesh": "central", "Chhattisgarh": "central",
    "Rajasthan": "west", "Gujarat": "west", "Maharashtra": "west", "Goa": "west", "Tamil Nadu": "south",
    "Kerala": "south", "Karnataka": "south", "Andhra Pradesh": "south", "Telangana": "south", "Odisha": "east",
    "West Bengal": "east", "Bihar": "east", "Jharkhand": "east", "Assam": "northeast", "Manipur": "northeast",
    "Meghalaya": "northeast", "Mizoram": "northeast", "Nagaland": "northeast", "Tripura": "northeast",
    "Sikkim": "northeast", "Arunachal Pradesh": "northeast",
}
SAFE_TEXT = r"^[\w .,&'()\-/\u0900-\u0DFF]*$"


class ProfileIn(BaseModel):
    owner_name: str | None = Field(None, max_length=80, pattern=SAFE_TEXT)
    phone: str | None = Field(None, pattern=r"^[6-9]\d{9}$")
    pan: str | None = Field(None, pattern=r"^[A-Z]{5}\d{4}[A-Z]$")
    aadhaar_last4: str | None = Field(None, pattern=r"^\d{4}$")
    udyam_number: str | None = Field(None, pattern=r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")
    gender: str | None = Field(None, pattern=r"^(female|male|transgender|undisclosed)$")
    social_category: str | None = Field(None, pattern=r"^(general|sc|st|obc|minority|undisclosed)$")
    age: int | None = Field(None, ge=14, le=100)
    education: str | None = Field(None, pattern=r"^(none|below_8|8th_pass|10th|12th|graduate)$")
    is_new_unit: bool | None = None
    is_first_venture: bool | None = None
    prior_default: bool | None = None
    availed_govt_subsidy: bool | None = None
    prior_mudra_tarun_repaid: bool | None = None
    prior_similar_scheme_loan_5y: bool | None = None
    prior_similar_loan_repaid: bool | None = None
    govt_employee_in_family: bool | None = None
    artisan_trade: str | None = Field(None, max_length=40, pattern=SAFE_TEXT)
    street_vendor: bool | None = None
    has_vending_certificate: bool | None = None
    is_shg: bool | None = None
    shg_months_active: int | None = Field(None, ge=0, le=600)
    shg_books_maintained: bool | None = None
    ex_serviceman: bool | None = None
    differently_abled: bool | None = None
    has_itr: bool | None = None
    has_audited_statements: bool | None = None


class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=120, pattern=SAFE_TEXT)
    sector: str = Field(pattern=r"^(tailoring|fabrication|dairy|food_processing|handicraft|retail|services|other)$")
    activity_type: str = Field(pattern=r"^(manufacturing|services|trading|agri_allied)$")
    state: str = Field(min_length=2, max_length=60, pattern=SAFE_TEXT)
    district: str = Field(min_length=2, max_length=80, pattern=SAFE_TEXT)
    area: str = Field(pattern=r"^(rural|urban)$")
    lat: float = Field(22.0, ge=6, le=37)
    lng: float = Field(79.0, ge=68, le=98)
    years_in_operation: float = Field(0, ge=0, le=80)
    employees: int = Field(1, ge=0, le=500)
    loan_need: int = Field(0, ge=0, le=100_000_000)
    loan_purpose: str = Field("working_capital", pattern=r"^(working_capital|machinery|expansion|new_unit|livestock)$")
    profile: ProfileIn = ProfileIn()


def summary(b: Business) -> dict:
    return {"id": b.id, "name": b.name, "sector": b.sector, "activity_type": b.activity_type, "state": b.state,
            "district": b.district, "region": b.region, "area": b.area, "lat": b.lat, "lng": b.lng,
            "years_in_operation": b.years_in_operation, "employees": b.employees, "loan_need": b.loan_need,
            "loan_purpose": b.loan_purpose, "shredded": b.shredded}


def _apply(b: Business, body: BusinessIn):
    for k in ("name", "sector", "activity_type", "state", "district", "area", "lat", "lng", "years_in_operation",
              "employees", "loan_need", "loan_purpose"):
        setattr(b, k, getattr(body, k))
    b.region = REGION_OF.get(body.state.title(), "central")


@router.get("/businesses")
def list_businesses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ids = consent.visible_business_ids(db, user)
    return [summary(b) for b in db.query(Business).filter(Business.id.in_(ids)).all()] if ids else []


@router.post("/businesses")
def create_business(body: BusinessIn, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    if db.query(Business).filter(Business.owner_id == user.id).first():
        raise HTTPException(409, "You already have a business profile")
    if not user.dek_wrapped:
        user.dek_wrapped = new_wrapped_dek(user.id)
    b = Business(owner_id=user.id, region="central")
    _apply(b, body)
    db.add(b)
    db.flush()
    write_profile(b, body.profile.model_dump(exclude_none=True))
    audit.record(db, user, "business.created", b.id, {"sector": b.sector, "district": b.district})
    return summary(b)


@router.get("/businesses/{business_id}")
def get_business_detail(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile")
    profile = read_profile(b)
    if user.role != "entrepreneur":
        profile = {**{k: v for k, v in profile.items() if k not in ("pan", "phone", "udyam_number", "aadhaar_last4")},
                   **{k: v for k, v in masked_profile(b, profile).items() if k in ("pan", "phone", "udyam_number", "aadhaar")}}
    return {**summary(b), "profile": profile}


@router.put("/businesses/{business_id}")
def update_business(business_id: int, body: BusinessIn, user: User = Depends(require_roles("entrepreneur", "agent")),
                    db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile", log=False)
    _apply(b, body)
    current = read_profile(b)
    incoming = body.profile.model_dump(exclude_none=True)
    if user.role == "agent":  # agents may not overwrite identifiers
        for k in ("pan", "phone", "udyam_number", "aadhaar_last4"):
            incoming.pop(k, None)
    current.update(incoming)
    write_profile(b, current)
    audit.record(db, user, "business.updated", b.id, {"fields": sorted(incoming)})
    return summary(b)


class IntakeIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


@router.post("/agents/intake")
def run_intake(body: IntakeIn, user: User = Depends(current_user)):
    from ..security import redact
    clean, found = redact(body.text)
    return {**intake.parse(clean), "redacted": found}


# ---------- consent ----------
class ConsentIn(BaseModel):
    grantee_type: str = Field(pattern=r"^(platform|agent|lender|dic)$")
    grantee_org: str = Field("", max_length=160, pattern=SAFE_TEXT.replace("]*$", "·]*$"))
    purpose: str
    scopes: list[str] = Field(min_length=1, max_length=6)
    days: int = Field(90, ge=1, le=365)


def consent_out(c: Consent) -> dict:
    consent.refresh_status(c)
    return {"id": c.id, "grantee_type": c.grantee_type, "grantee_org": c.grantee_org, "purpose": c.purpose,
            "purpose_text": consent.PURPOSES.get(c.purpose), "scopes": c.scopes, "status": c.status,
            "granted_at": c.granted_at.isoformat(), "expires_at": c.expires_at.isoformat(),
            "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None, "artefact_hash": c.artefact_hash,
            "signature": c.signature}


@router.get("/consent/catalog")
def consent_catalog(user: User = Depends(current_user)):
    from ..workflows import LENDERS
    return {"purposes": consent.PURPOSES, "scopes": consent.SCOPES, "platform_org": consent.PLATFORM_ORG,
            "agents": ["Jan Seva BC Network"], "lenders": LENDERS}


@router.get("/businesses/{business_id}/consents")
def list_consents(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    q = db.query(Consent).filter(Consent.business_id == b.id)
    if user.role == "entrepreneur":
        if b.owner_id != user.id:
            raise HTTPException(404, "Business not found")
    elif user.role in ("agent", "lender", "dic"):
        q = q.filter(Consent.grantee_org == user.org)
    else:
        raise HTTPException(403, "Not permitted")
    out = [consent_out(c) for c in q.order_by(Consent.id.desc()).all()]
    db.commit()
    return out


@router.post("/businesses/{business_id}/consents")
def grant_consent(business_id: int, body: ConsentIn, user: User = Depends(require_roles("entrepreneur")),
                  db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile")
    org = consent.PLATFORM_ORG if body.grantee_type == "platform" else body.grantee_org.strip()
    if not org:
        raise HTTPException(422, "Choose who you are sharing with")
    c = consent.grant(db, user, b, body.grantee_type, org, body.purpose, body.scopes, body.days)
    return consent_out(c)


@router.post("/consents/{consent_id}/revoke")
def revoke_consent(consent_id: int, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    c = db.get(Consent, consent_id)
    if not c:
        raise HTTPException(404, "Consent not found")
    consent.authorize(db, user, get_business(db, c.business_id), "profile")
    return consent_out(consent.revoke(db, user, c))


@router.get("/businesses/{business_id}/access-log")
def access_log(business_id: int, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile")
    rows = (db.query(AuditLog).filter(AuditLog.business_id == b.id).order_by(AuditLog.id.desc()).limit(200).all())
    actors = {u.id: u for u in db.query(User).filter(User.id.in_({r.actor_id for r in rows if r.actor_id})).all()}
    return [{"id": r.id, "ts": r.ts, "action": r.action, "actor_role": r.actor_role,
             "actor": ("You" if r.actor_id == user.id else (actors[r.actor_id].org or actors[r.actor_id].role)
                       if r.actor_id in actors else "system"),
             "details": r.details, "hash": r.hash} for r in rows]


# ---------- cash-flow ----------
def _store_dataset(db, user, b, txns, source):
    c = consent.platform_consent(db, b, "upi_transactions")
    ds = CashflowDataset(business_id=b.id, consent_id=c.id, source=source, row_count=len(txns),
                         sha256=sha256_hex(repr(txns).encode()), data_enc=b"")
    db.add(ds)
    db.flush()
    ds.data_enc = encrypt_json(owner_dek(b), txns, f"cashflow:{b.id}:{ds.id}")
    audit.record(db, user, "cashflow.ingested", b.id, {"source": source, "rows": len(txns), "consent_id": c.id,
                                                       "sha256": ds.sha256})
    return ds


@router.post("/businesses/{business_id}/cashflow/upload")
async def upload_cashflow(business_id: int, file: UploadFile = File(...),
                          user: User = Depends(require_roles("entrepreneur", "agent")), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "upi_transactions", log=False)
    consent.platform_consent(db, b, "upi_transactions")
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")
    txns = cashflow.parse_csv(raw, b.id)
    ds = _store_dataset(db, user, b, txns, "upi_csv_upload")
    return {"dataset_id": ds.id, "rows": ds.row_count}


@router.post("/businesses/{business_id}/cashflow/fetch")
def fetch_cashflow(business_id: int, user: User = Depends(require_roles("entrepreneur", "agent")),
                   db: Session = Depends(get_db)):
    """Simulated Account-Aggregator pull (demo): generates a realistic 12-month UPI statement."""
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "upi_transactions", log=False)
    consent.platform_consent(db, b, "upi_transactions")
    base = max(25_000, (b.loan_need or 200_000) / 4)
    txns = cashflow.synthetic_upi(b.id * 31 + len(b.name), base, cv=0.22, payers=30, business_id=b.id)
    ds = _store_dataset(db, user, b, txns, "account_aggregator_simulated")
    return {"dataset_id": ds.id, "rows": ds.row_count}


@router.get("/businesses/{business_id}/cashflow")
def get_cashflow(business_id: int, include_lines: bool = False, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "upi_transactions" if include_lines else "cashflow_summary")
    if user.role == "entrepreneur":
        consent.platform_consent(db, b, "cashflow_summary")
    ds = latest_dataset(db, b)
    if not ds:
        return {"available": False}
    tx = transactions(db, b)
    a = cashflow.analyse(tx, b.years_in_operation)
    out = {"available": True, "dataset": {"id": ds.id, "source": ds.source, "rows": ds.row_count,
                                          "uploaded_at": ds.uploaded_at.isoformat(), "sha256": ds.sha256}, **a}
    if include_lines:
        out["lines"] = tx[-200:]
    return out


@router.get("/businesses/{business_id}/eligibility")
def get_eligibility(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "eligibility")
    from ..agents import eligibility
    return eligibility.evaluate(b, read_profile(b))


@router.get("/businesses/{business_id}/risk")
def get_risk(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "risk_report")
    if user.role == "entrepreneur":
        consent.platform_consent(db, b, "risk_report")
    tx = transactions(db, b)
    if not tx:
        return {"available": False}
    a = cashflow.analyse(tx, b.years_in_operation)
    return {"available": True, **model().assess(a["features"]), "features": a["features"]}


# ---------- documents ----------
MAGIC = {b"%PDF": "application/pdf", b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}


@router.get("/businesses/{business_id}/documents")
def get_documents(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "documents")
    return context(db, b)["documents"]


@router.post("/businesses/{business_id}/documents")
async def upload_document(business_id: int, doc_type: str = Form(..., pattern=r"^[a-z_]{2,40}$"),
                          file: UploadFile = File(...), user: User = Depends(require_roles("entrepreneur", "agent")),
                          db: Session = Depends(get_db)):
    from ..agents.schemes import DOCUMENTS
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "documents", log=False)
    if doc_type not in DOCUMENTS:
        raise HTTPException(422, "Unknown document type")
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")
    mime = next((m for sig, m in MAGIC.items() if raw.startswith(sig)), None)
    if not mime:
        raise HTTPException(415, "Only PDF, PNG or JPEG files are accepted")
    name = re.sub(r"[^\w.\-]", "_", (file.filename or "document"))[-80:]
    for old in db.query(Document).filter(Document.business_id == b.id, Document.doc_type == doc_type).all():
        db.delete(old)
    d = Document(business_id=b.id, doc_type=doc_type, filename=name, mime=mime, size=len(raw),
                 sha256=sha256_hex(raw), uploaded_by=user.id)
    db.add(d)
    db.flush()
    d.content_enc = encrypt_bytes(owner_dek(b), raw, f"doc:{b.id}:{d.id}")
    audit.record(db, user, "document.uploaded", b.id, {"doc_type": doc_type, "sha256": d.sha256, "size": d.size})
    return {"id": d.id, "doc_type": doc_type, "sha256": d.sha256}


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    b = get_business(db, d.business_id)
    consent.authorize(db, user, b, "documents")
    raw = decrypt_bytes(owner_dek(b), d.content_enc, f"doc:{b.id}:{d.id}")
    return Response(raw, media_type=d.mime, headers={
        "Content-Disposition": f'attachment; filename="{d.filename}"', "Cache-Control": "no-store"})


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, user: User = Depends(require_roles("entrepreneur")), db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    b = get_business(db, d.business_id)
    consent.authorize(db, user, b, "documents")
    db.delete(d)
    audit.record(db, user, "document.deleted", b.id, {"doc_type": d.doc_type})
    return {"ok": True}


# ---------- agents ----------
@router.post("/businesses/{business_id}/agents/run")
def run_agents(business_id: int, user: User = Depends(require_roles("entrepreneur", "agent")),
               db: Session = Depends(get_db)):
    b = get_business(db, business_id)
    consent.authorize(db, user, b, "profile")
    return orchestrator.run(db, user, b)


class ChatIn(BaseModel):
    business_id: int | None = None
    message: str = Field(min_length=1, max_length=1000)


@router.post("/agents/chat")
def agent_chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = None
    if body.business_id:
        b = get_business(db, body.business_id)
        consent.authorize(db, user, b, "profile", log=False)
    return orchestrator.chat(db, user, b, body.message)


@router.get("/agents/catalog")
def agent_catalog(user: User = Depends(current_user)):
    return orchestrator.AGENTS
