"""Export a read-only snapshot of the synthetic demo for static hosting (no backend).

Run from backend/:  python scripts/export_demo.py ../frontend/src/demo/snapshot.json
Only seeded synthetic data is exported; never run against a database with real users.
"""
import json
import os
import sys
import tempfile

os.environ["ARTHA_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ARTHA_SEED_DEMO"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import limiter  # noqa: E402

PW = "Artha@Demo2026"
PERSONAS = ["lakshmi@artha.demo", "ravi@artha.demo", "meena@artha.demo", "gurpreet@artha.demo",
            "bc@artha.demo", "manager@artha.demo", "dic@artha.demo", "auditor@artha.demo"]
PROMPTS = ["Which schemes am I eligible for?", "Why is my score what it is?", "What documents do I need?",
           "How much will I save vs the moneylender?", "Where is my application stuck?", "Who can see my data?",
           "What does the agent charge?"]
GLOBAL = ["/auth/me", "/businesses", "/agents/catalog", "/analytics/overview", "/analytics/money-trail", "/applications",
          "/applications-meta", "/audit/verify", "/audit?limit=200", "/consent/catalog", "/field/insights",
          "/model/card", "/me/export", "/schemes"]
PER_BIZ = ["access-log", "cashflow", "consents", "documents", "eligibility", "risk"]


def grab(c, method, path, **kw):
    limiter._hits.clear()
    r = c.request(method, "/api" + path, **kw)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        return {"__status": r.status_code, "detail": detail if isinstance(detail, str) else "Request failed"}
    return r.json()


def main(out):
    snap = {"password": PW, "personas": {}}
    with TestClient(app) as c:
        for email in PERSONAS:
            c.cookies.clear()
            assert grab(c, "POST", "/auth/login", json={"email": email, "password": PW}).get("user"), email
            h = {"x-csrf-token": c.cookies.get("artha_csrf")}
            get = {p: grab(c, "GET", p) for p in GLOBAL}
            post = {}
            for b in get["/businesses"] if isinstance(get["/businesses"], list) else []:
                for s in PER_BIZ:
                    get[f"/businesses/{b['id']}/{s}"] = grab(c, "GET", f"/businesses/{b['id']}/{s}")
            for a in get["/applications"] if isinstance(get["/applications"], list) else []:
                get[f"/applications/{a['id']}"] = grab(c, "GET", f"/applications/{a['id']}")
            for b in get["/businesses"] if isinstance(get["/businesses"], list) else []:
                post[f"/businesses/{b['id']}/agents/run"] = grab(c, "POST", f"/businesses/{b['id']}/agents/run", headers=h)
                post[f"/businesses/{b['id']}/cashflow/fetch"] = grab(c, "POST", f"/businesses/{b['id']}/cashflow/fetch", headers=h)
                for q in PROMPTS:
                    post[f"chat:{b['id']}:{q}"] = grab(c, "POST", "/agents/chat", headers=h, json={"business_id": b["id"], "message": q})
            snap["personas"][email] = {"get": get, "post": post}
            c.post("/api/auth/logout", headers=h)
    with open(out, "w") as fh:
        json.dump(snap, fh, separators=(",", ":"))
    print(out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../frontend/src/demo/snapshot.json")
