from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # entrepreneur | agent | lender | dic | auditor
    display_name: Mapped[str] = mapped_column(String(120))
    org: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dek_wrapped: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str] = mapped_column(String(40))
    activity_type: Mapped[str] = mapped_column(String(30))  # manufacturing | services | trading | agri_allied
    state: Mapped[str] = mapped_column(String(60))
    district: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(20))
    area: Mapped[str] = mapped_column(String(10))  # rural | urban
    lat: Mapped[float] = mapped_column(Float, default=0)
    lng: Mapped[float] = mapped_column(Float, default=0)
    years_in_operation: Mapped[float] = mapped_column(Float, default=0)
    employees: Mapped[int] = mapped_column(Integer, default=1)
    loan_need: Mapped[int] = mapped_column(Integer, default=0)
    loan_purpose: Mapped[str] = mapped_column(String(30), default="working_capital")
    profile_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    shredded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    owner: Mapped[User] = relationship()


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    grantee_type: Mapped[str] = mapped_column(String(20))  # platform | agent | lender | dic
    grantee_org: Mapped[str] = mapped_column(String(160))
    purpose: Mapped[str] = mapped_column(String(40))
    scopes: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(12), default="active")
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    artefact_hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(120))


class CashflowDataset(Base):
    __tablename__ = "cashflow_datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    consent_id: Mapped[int] = mapped_column(ForeignKey("consents.id"))
    source: Mapped[str] = mapped_column(String(40))
    row_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    data_enc: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(160))
    mime: Mapped[str] = mapped_column(String(60))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(20), default="upload")  # upload | digilocker | aa
    content_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(20), unique=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    scheme_id: Mapped[str] = mapped_column(String(40))
    lender_org: Mapped[str] = mapped_column(String(160), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    completeness: Mapped[float] = mapped_column(Float, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_signature: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_id: Mapped[int | None] = mapped_column(ForeignKey("consents.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    snapshot_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(60), index=True)
    business_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(120))


class FieldInterview(Base):
    __tablename__ = "field_interviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    respondent_type: Mapped[str] = mapped_column(String(30))
    sector: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(60))
    answers: Mapped[dict] = mapped_column(JSON)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RateBucket(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str] = mapped_column(Text, default="")
