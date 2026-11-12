import os
import tempfile

os.environ["ARTHA_DATA_DIR"] = tempfile.mkdtemp()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PW = "Artha@Demo2026"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(c, email, pw=PW):
    from app.security import limiter
    limiter._hits.clear()
    c.cookies.clear()
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"x-csrf-token": r.json()["csrf"]}


def biz_id(c):
    return c.get("/api/businesses").json()[0]["id"]


def test_requires_auth(client):
    client.cookies.clear()
    assert client.get("/api/businesses").status_code == 401


def test_security_headers(client):
    r = client.get("/api/health")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_session_cookie_is_httponly(client):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": "lakshmi@artha.demo", "password": PW})
    cookie = [h for h in r.headers.get_list("set-cookie") if h.startswith("artha_session")][0]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie


def test_csrf_enforced(client):
    login(client, "lakshmi@artha.demo")
    assert client.post(f"/api/businesses/{biz_id(client)}/agents/run").status_code == 403


def test_owner_cannot_read_other_business(client):
    login(client, "ravi@artha.demo")
    ravi = biz_id(client)
    login(client, "lakshmi@artha.demo")
    assert client.get(f"/api/businesses/{ravi}").status_code == 404


def test_data_encrypted_at_rest(client):
    from app.db import SessionLocal
    from app.models import Business
    with SessionLocal() as db:
        b = db.query(Business).filter(Business.name == "Lakshmi Tailoring Works").first()
        assert b"ABCPL1234K" not in b.profile_enc and b"female" not in b.profile_enc


def test_lender_sees_masked_pii_and_access_is_logged(client):
    login(client, "manager@artha.demo")
    apps = client.get("/api/applications").json()
    assert apps and all(a["status"] not in ("draft", "awaiting_owner_approval") for a in apps)
    lak = next(a for a in apps if a["business_name"] == "Lakshmi Tailoring Works")
    d = client.get(f"/api/applications/{lak['id']}").json()
    assert "ABCPL1234K" not in str(d) and d["snapshot"]["applicant"]["pan"].endswith("234K")
    login(client, "lakshmi@artha.demo")
    log = client.get(f"/api/businesses/{biz_id(client)}/access-log").json()
    assert any(e["action"] == "data.accessed" and "Navodaya" in e["actor"] for e in log)


def test_revoking_consent_blocks_lender(client):
    h = login(client, "lakshmi@artha.demo")
    bid = biz_id(client)
    c = next(x for x in client.get(f"/api/businesses/{bid}/consents").json()
             if x["grantee_type"] == "lender" and x["status"] == "active")
    assert client.post(f"/api/consents/{c['id']}/revoke", headers=h).status_code == 200
    login(client, "manager@artha.demo")
    app_id = next(a["id"] for a in client.get("/api/applications").json() if a["business_name"] == "Lakshmi Tailoring Works")
    assert client.get(f"/api/applications/{app_id}").status_code == 403


def test_only_owner_can_approve_with_password(client):
    h = login(client, "bc@artha.demo")
    pending = [a for a in client.get("/api/applications").json() if a["status"] == "awaiting_owner_approval"]
    assert pending
    aid = pending[0]["id"]
    assert client.post(f"/api/applications/{aid}/approve", json={"password": PW, "confirm": True}, headers=h).status_code == 403
    h = login(client, "lakshmi@artha.demo")
    assert client.post(f"/api/applications/{aid}/approve", json={"password": "wrong", "confirm": True}, headers=h).status_code == 401
    r = client.post(f"/api/applications/{aid}/approve", json={"password": PW, "confirm": True}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "submitted" and r.json()["approval_signature"]


def test_rejection_requires_reason(client):
    h = login(client, "manager@artha.demo")
    a = next(x for x in client.get("/api/applications").json() if x["status"] in ("submitted", "under_review"))
    assert client.post(f"/api/applications/{a['id']}/decision", json={"action": "rejected"}, headers=h).status_code == 422


def test_upload_rejects_non_pdf(client):
    h = login(client, "lakshmi@artha.demo")
    r = client.post(f"/api/businesses/{biz_id(client)}/documents", data={"doc_type": "quotation"},
                    files={"file": ("x.pdf", b"<script>alert(1)</script>", "application/pdf")}, headers=h)
    assert r.status_code == 415


def test_eligibility_has_citations(client):
    login(client, "lakshmi@artha.demo")
    for s in client.get(f"/api/businesses/{biz_id(client)}/eligibility").json():
        for chk in s["checks"]:
            assert chk["citation"]["url"].startswith("https://")


def test_model_fairness_and_no_protected_inputs(client):
    login(client, "auditor@artha.demo")
    card = client.get("/api/model/card").json()
    keys = {f["key"] for f in card["features"]}
    assert not keys & {"gender", "region", "social_category"}
    for attr in ("gender", "region"):
        assert all(card["fairness"][attr]["checks"].values())
    assert card["metrics"]["ece"] < 0.03


def test_chat_redacts_pii(client):
    h = login(client, "lakshmi@artha.demo")
    r = client.post("/api/agents/chat", json={"business_id": biz_id(client), "message": "my phone 9876543210 schemes?"},
                    headers=h).json()
    assert "9876543210" not in r["sanitised_input"] and "PHONE" in r["redacted"]


def test_audit_chain_detects_tampering(client):
    from app.audit import verify_chain
    from app.db import SessionLocal
    from app.models import AuditLog
    with SessionLocal() as db:
        assert verify_chain(db)["valid"]
        e = db.query(AuditLog).order_by(AuditLog.id).offset(3).first()
        orig = e.action
        e.action = "tampered"
        db.flush()
        assert not verify_chain(db)["valid"]
        e.action = orig
        db.rollback()


def test_lockout_after_failed_logins(client):
    client.cookies.clear()
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "dic@artha.demo", "password": "nope"})
    r = client.post("/api/auth/login", json={"email": "dic@artha.demo", "password": PW})
    assert r.status_code in (423, 429)


def test_crypto_shred(client):
    h = login(client, "gurpreet@artha.demo")
    bid = biz_id(client)
    assert client.post("/api/me/erase", json={"password": PW, "confirm_text": "ERASE"}, headers=h).status_code == 200
    from app.db import SessionLocal
    from app.models import Business
    with SessionLocal() as db:
        b = db.get(Business, bid)
        assert b.shredded and b.profile_enc is None and b.owner.dek_wrapped is None
