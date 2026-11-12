"""Access to encrypted business data via the owner's per-user data key (crypto-shreddable)."""
from fastapi import HTTPException

from .crypto import decrypt_json, encrypt_json, unwrap_dek
from .models import Business, User


def owner_dek(business: Business) -> bytes:
    owner: User = business.owner
    if business.shredded or not owner.dek_wrapped:
        raise HTTPException(410, "This business's data has been erased at the owner's request")
    return unwrap_dek(owner.dek_wrapped, owner.id)


def read_profile(business: Business) -> dict:
    if not business.profile_enc:
        return {}
    return decrypt_json(owner_dek(business), business.profile_enc, f"profile:{business.id}")


def write_profile(business: Business, profile: dict) -> None:
    business.profile_enc = encrypt_json(owner_dek(business), profile, f"profile:{business.id}")
