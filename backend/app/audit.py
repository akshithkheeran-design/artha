"""Tamper-evident audit trail: every entry is hash-chained and Ed25519-signed. No PII in details."""
import threading

from sqlalchemy.orm import Session

from .crypto import canonical, sha256_hex, sign, verify
from .models import AuditLog, utcnow

_lock = threading.Lock()
GENESIS = "0" * 64


def _body(e: AuditLog) -> dict:
    return {
        "ts": e.ts, "actor_id": e.actor_id, "actor_role": e.actor_role, "action": e.action,
        "business_id": e.business_id, "details": e.details or {}, "prev_hash": e.prev_hash,
    }


def record(db: Session, actor, action: str, business_id: int | None = None, details: dict | None = None,
           commit: bool = True) -> AuditLog:
    with _lock:
        last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        entry = AuditLog(
            ts=utcnow().isoformat(timespec="milliseconds") + "Z",
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", None) or (actor if isinstance(actor, str) else "system"),
            action=action, business_id=business_id, details=details or {},
            prev_hash=last.hash if last else GENESIS,
        )
        entry.hash = sha256_hex(canonical(_body(entry)))
        entry.signature = sign(entry.hash.encode())
        db.add(entry)
        if commit:
            db.commit()
        else:
            db.flush()
        return entry


def verify_chain(db: Session) -> dict:
    prev = GENESIS
    count = 0
    for e in db.query(AuditLog).order_by(AuditLog.id.asc()).yield_per(500):
        count += 1
        if e.prev_hash != prev:
            return {"valid": False, "entries": count, "broken_at": e.id, "reason": "prev_hash mismatch"}
        if sha256_hex(canonical(_body(e))) != e.hash:
            return {"valid": False, "entries": count, "broken_at": e.id, "reason": "content hash mismatch"}
        if not verify(e.signature, e.hash.encode()):
            return {"valid": False, "entries": count, "broken_at": e.id, "reason": "bad signature"}
        prev = e.hash
    return {"valid": True, "entries": count, "head": prev}
