from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .. import audit
from ..crypto import new_wrapped_dek
from ..db import get_db
from ..models import User, utcnow
from ..security import (clear_session, client_ip, current_user, hash_password, issue_session, limiter,
                        password_ok, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])
MAX_FAILS, LOCK_MINUTES = 5, 15


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80, pattern=r"^[\w .'\-\u0900-\u0DFF]+$")


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "role": u.role, "display_name": u.display_name, "org": u.org}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not limiter.hit(f"login:{ip}", 10, 60) or not limiter.hit(f"login:{body.email.lower()}", 10, 300):
        raise HTTPException(429, "Too many login attempts — try again in a few minutes")
    user = db.query(User).filter(User.email == body.email.lower()).first()
    now = utcnow()
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(423, "Account temporarily locked after repeated failures")
    if not verify_password(body.password, user.password_hash if user else None):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILS:
                user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                user.failed_logins = 0
            audit.record(db, user, "auth.login_failed", None, {})
        raise HTTPException(401, "Invalid email or password")
    user.failed_logins = 0
    user.locked_until = None
    audit.record(db, user, "auth.login", None, {})
    return {"user": user_out(user), **issue_session(response, user)}


@router.post("/register")
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if not limiter.hit(f"register:{client_ip(request)}", 5, 3600):
        raise HTTPException(429, "Too many sign-ups from this network")
    if not password_ok(body.password):
        raise HTTPException(422, "Password needs 10+ characters with upper-case, lower-case and a digit")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "An account with this email already exists")
    u = User(email=body.email.lower(), password_hash=hash_password(body.password), role="entrepreneur",
             display_name=body.display_name.strip())
    db.add(u)
    db.flush()
    u.dek_wrapped = new_wrapped_dek(u.id)
    audit.record(db, u, "auth.registered", None, {})
    return {"user": user_out(u), **issue_session(response, u)}


@router.post("/logout")
def logout(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    audit.record(db, user, "auth.logout", None, {})
    clear_session(response)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user": user_out(user)}
