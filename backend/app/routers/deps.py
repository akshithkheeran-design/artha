from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Business


def get_business(db: Session, business_id: int) -> Business:
    b = db.get(Business, business_id)
    if not b:
        raise HTTPException(404, "Business not found")
    return b
