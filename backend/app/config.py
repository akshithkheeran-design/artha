import base64
import hashlib
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("ARTHA_DATA_DIR", BASE_DIR / "var"))
DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

ENV = os.getenv("ARTHA_ENV", "development")
DATABASE_URL = os.getenv("ARTHA_DATABASE_URL", f"sqlite:///{DATA_DIR / 'artha.db'}")
COOKIE_SECURE = os.getenv("ARTHA_COOKIE_SECURE", "true" if ENV == "production" else "false") == "true"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ARTHA_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
SESSION_MINUTES = int(os.getenv("ARTHA_SESSION_MINUTES", "30"))
MAX_UPLOAD_BYTES = int(os.getenv("ARTHA_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
FRONTEND_DIST = Path(os.getenv("ARTHA_FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))
SEED_DEMO = os.getenv("ARTHA_SEED_DEMO", "false" if ENV == "production" else "true") == "true"


def _load_secret(name: str, env: str, nbytes: int) -> bytes:
    value = os.getenv(env)
    if value:
        if len(value) < 32:
            raise RuntimeError(f"{env} must be at least 32 characters of random data")
        try:
            raw = base64.b64decode(value, validate=True)
        except ValueError:
            raw = b""
        if len(raw) >= nbytes:
            return raw[:nbytes]
        return hashlib.shake_256(f"artha:{name}:".encode() + value.encode()).digest(nbytes)
    if ENV == "production":
        raise RuntimeError(f"{env} must be set in production (base64, from a secrets manager)")
    path = DATA_DIR / f"{name}.key"
    if path.exists():
        return path.read_bytes()
    raw = secrets.token_bytes(nbytes)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(raw)
    return raw


MASTER_KEY = _load_secret("master", "ARTHA_MASTER_KEY", 32)
JWT_SECRET = _load_secret("jwt", "ARTHA_JWT_SECRET", 64)
SIGNING_SEED = _load_secret("signing", "ARTHA_SIGNING_SEED", 32)
INDEX_KEY = _load_secret("index", "ARTHA_INDEX_KEY", 32)
