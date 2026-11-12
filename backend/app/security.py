import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .config import COOKIE_SECURE, JWT_SECRET, SESSION_MINUTES
from .db import get_db
from .models import User

SESSION_COOKIE = "artha_session"
CSRF_COOKIE = "artha_csrf"
CSRF_HEADER = "x-csrf-token"
ROLES = {"entrepreneur", "agent", "lender", "dic", "auditor"}

_ph = PasswordHasher()  # Argon2id defaults
_DUMMY_HASH = _ph.hash(secrets.token_urlsafe(16))


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str | None) -> bool:
    try:
        return _ph.verify(hashed or _DUMMY_HASH, pw) and hashed is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


PASSWORD_RULE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{10,128}$")


def password_ok(pw: str) -> bool:
    return bool(PASSWORD_RULE.match(pw))


def csrf_for(jti: str) -> str:
    return hmac.new(JWT_SECRET, f"csrf:{jti}".encode(), hashlib.sha256).hexdigest()


def issue_session(response: Response, user: User) -> dict:
    jti = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user.id), "role": user.role, "tv": user.token_version, "jti": jti,
         "iat": now, "exp": now + timedelta(minutes=SESSION_MINUTES), "iss": "artha"},
        JWT_SECRET, algorithm="HS256")
    csrf = csrf_for(jti)
    max_age = SESSION_MINUTES * 60
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=COOKIE_SECURE,
                        samesite="strict", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_age, httponly=False, secure=COOKIE_SECURE,
                        samesite="strict", path="/")
    return {"csrf": csrf, "expires_in": max_age}


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def _decode(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"], issuer="artha")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid session")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    claims = _decode(request)
    user = db.get(User, int(claims["sub"]))
    if not user or user.token_version != claims.get("tv"):
        raise HTTPException(401, "Session revoked")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not hmac.compare_digest(sent, csrf_for(claims["jti"])):
            raise HTTPException(403, "CSRF token missing or invalid")
    request.state.user = user
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Your role is not permitted to perform this action")
        return user
    return dep


class RateLimiter:
    """In-memory sliding window limiter (per process)."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: float) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


PII_PATTERNS = [
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I), "[PAN]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"), "[PHONE]"),
    (re.compile(r"\b[\w.\-]+@[\w.\-]+\.[a-z]{2,}\b", re.I), "[EMAIL]"),
    (re.compile(r"\b[\w.\-]{2,}@[a-z]{2,}\b", re.I), "[UPI-ID]"),
    (re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", re.I), "[UDYAM]"),
]


def redact(text: str) -> tuple[str, list[str]]:
    found = []
    for pat, label in PII_PATTERNS:
        if pat.search(text):
            found.append(label.strip("[]"))
            text = pat.sub(label, text)
    return text, found


def mask(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return value
    v = str(value)
    return "•" * max(0, len(v) - keep) + v[-keep:]
