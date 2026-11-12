from sqlalchemy.orm import Session

from .agents import cashflow, documents, eligibility, risk
from .crypto import decrypt_json
from .models import Business, CashflowDataset, Document
from .vault import owner_dek, read_profile


def latest_dataset(db: Session, business: Business) -> CashflowDataset | None:
    return (db.query(CashflowDataset).filter(CashflowDataset.business_id == business.id)
            .order_by(CashflowDataset.id.desc()).first())


def transactions(db: Session, business: Business) -> list[dict] | None:
    ds = latest_dataset(db, business)
    if not ds:
        return None
    return decrypt_json(owner_dek(business), ds.data_enc, f"cashflow:{business.id}:{ds.id}")


def cash_analysis(db: Session, business: Business) -> dict | None:
    tx = transactions(db, business)
    return cashflow.analyse(tx, business.years_in_operation) if tx else None


def context(db: Session, business: Business, target_scheme: str | None = None) -> dict:
    profile = read_profile(business)
    cash = cash_analysis(db, business)
    elig = eligibility.evaluate(business, profile)
    rk = risk.model().assess(cash["features"]) if cash else None
    docs = documents.checklist(business, profile, elig,
                               db.query(Document).filter(Document.business_id == business.id).all(),
                               cash is not None, target_scheme)
    return {"profile": profile, "cash": cash, "eligibility": elig, "risk": rk, "documents": docs}
