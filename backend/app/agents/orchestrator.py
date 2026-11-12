"""Orchestrator: plans and runs the specialist agents, keeping every step explainable and audited."""
import time

from sqlalchemy.orm import Session

from .. import audit, consent
from ..models import Application, Business, User
from ..security import redact
from ..services import context
from . import applications as appl
from .risk import model
from .schemes import SCHEME_INDEX

AGENTS = [
    {"id": "consent", "name": "Consent Guardian", "desc": "Checks a valid, purpose-bound consent exists before any data is touched."},
    {"id": "intake", "name": "Intake Agent", "desc": "Builds the business profile from conversation (English / Hinglish), asks only what is missing."},
    {"id": "cashflow", "name": "Cash-flow Analyst", "desc": "Turns consented UPI lines into volatility, surplus, customer-base and informal-debt signals."},
    {"id": "schemes", "name": "Scheme Navigator", "desc": "Rule engine over MUDRA, PMEGP, Stand-Up India, CGTMSE and more — every rule cites its source."},
    {"id": "risk", "name": "Risk Assessor", "desc": "Calibrated, explainable credit-readiness score; fairness audited across gender and region."},
    {"id": "documents", "name": "Document Agent", "desc": "Collapses 15–20 papers into a core pack; auto-fetches via DigiLocker / Account Aggregator."},
    {"id": "drafter", "name": "Application Drafter", "desc": "Prepares the lender-ready file. Cannot submit — the owner approves every application."},
    {"id": "audit", "name": "Audit Sentinel", "desc": "Hash-chains and signs every action into a tamper-evident trail."},
]


def _inr(n):
    n = int(n or 0)
    return f"₹{n / 100000:.2f} lakh" if n >= 100000 else f"₹{n:,}"


def run(db: Session, user: User, business: Business) -> dict:
    steps = []

    def step(agent, status, summary, details=None, citations=None, t0=None):
        steps.append({"agent": agent, "name": next(a["name"] for a in AGENTS if a["id"] == agent), "status": status,
                      "summary": summary, "details": details or {}, "citations": citations or [],
                      "ms": round((time.perf_counter() - t0) * 1000, 1) if t0 else 0})

    t = time.perf_counter()
    cf = consent.find_active(db, business.id, "platform", consent.PLATFORM_ORG, "upi_transactions")
    el = consent.find_active(db, business.id, "platform", consent.PLATFORM_ORG, "eligibility")
    step("consent", "ok" if cf else "warn",
         f"Cash-flow consent {'#' + str(cf.id) + ' active until ' + cf.expires_at.date().isoformat() if cf else 'missing'}; "
         f"eligibility consent {'active' if el else 'missing'}.",
         {"cashflow_consent": cf.id if cf else None, "eligibility_consent": el.id if el else None}, t0=t)

    t = time.perf_counter()
    ctx = context(db, business)
    cash, elig, rk, docs = ctx["cash"], ctx["eligibility"], ctx["risk"], ctx["documents"]
    filled = sum(v not in (None, "") for v in ctx["profile"].values())
    step("intake", "ok", f"Profile has {filled} verified fields; sector {business.sector}, {business.district}.", t0=t)

    t = time.perf_counter()
    if cash and cf:
        s = cash["summary"]
        step("cashflow", "ok", f"{s['transactions']} UPI lines over {s['months']} months · avg inflow "
             f"{_inr(s['avg_monthly_inflow'])}/month · sustainable EMI {_inr(s['sustainable_emi'])}.",
             {"insights": cash["insights"], "summary": s}, t0=t)
    else:
        step("cashflow", "skipped", "No consented cash-flow data yet — ask the owner to link UPI statement.", t0=t)

    t = time.perf_counter()
    ok = [e for e in elig if e["status"] == "eligible"]
    likely = [e for e in elig if e["status"] == "likely"]
    cites = {c["url"]: c for e in ok + likely for c in e["citations"]}
    step("schemes", "ok", f"{len(ok)} eligible, {len(likely)} likely (need info) out of {len(elig)} schemes. "
         + (f"Best match: {ok[0]['short']}." if ok else ""),
         {"eligible": [e["short"] for e in ok], "likely": [e["short"] for e in likely]}, list(cites.values()), t0=t)

    t = time.perf_counter()
    if rk:
        step("risk", "ok", f"Score {rk['score']} (band {rk['band']}), PD {rk['pd'] * 100:.1f}% "
             f"[90% CI {rk['pd_interval_90'][0] * 100:.1f}–{rk['pd_interval_90'][1] * 100:.1f}%], confidence {rk['confidence']}. "
             "Gender/region not used as inputs.", {"reason_codes": rk["reason_codes"], "strengths": rk["strengths"]}, t0=t)
    else:
        step("risk", "skipped", "Needs cash-flow data to compute a calibrated score.", t0=t)

    t = time.perf_counter()
    st = docs["stats"]
    step("documents", "ok", f"{st['required']} documents instead of ~{st['traditional']}: {st['ready']} ready, "
         f"{st['auto_fetchable']} auto-fetchable, {st['owner_must_upload']} to upload.", st, t0=t)

    t = time.perf_counter()
    rec = None
    if ok:
        best = ok[0]
        cap = SCHEME_INDEX[best["scheme_id"]]["max_amount"]
        amount = min(business.loan_need or cap, cap)
        if cash and cash["summary"]["suggested_loan_36m"] and best["scheme_id"] not in ("pmegp", "standup"):
            amount = min(amount, max(cash["summary"]["suggested_loan_36m"], 10000))
        rec = {"scheme_id": best["scheme_id"], "scheme": best["short"], "amount": int(amount),
               "also_apply": [e["short"] for e in ok[1:3]]}
        step("drafter", "ok", f"Recommend {best['short']} for {_inr(amount)}"
             + (f" (+ {', '.join(rec['also_apply'])})" if rec["also_apply"] else "") + ". Awaiting owner approval.", rec, t0=t)
    else:
        step("drafter", "warn", "No fully eligible scheme yet — answer the missing questions first.", t0=t)

    t = time.perf_counter()
    entry = audit.record(db, user, "agents.pipeline_run", business.id,
                         {"steps": [s["agent"] for s in steps], "recommendation": rec,
                          "model": model().card["version"]})
    step("audit", "ok", f"Run sealed in audit chain · entry #{entry.id} · {entry.hash[:16]}…",
         {"hash": entry.hash, "signature": entry.signature[:24] + "…"}, t0=t)
    return {"business_id": business.id, "steps": steps, "recommendation": rec}


INTENTS = [
    ("schemes", r"scheme|yojana|eligible|qualify|mudra|pmegp|stand.?up|cgtmse|subsidy|sarkari"),
    ("risk", r"score|risk|why|reject|chance|credit|cibil|approve"),
    ("documents", r"document|kagaz|paper|proof|upload|certificate"),
    ("savings", r"save|moneylender|sahukar|interest|byaj|cost|cheaper"),
    ("status", r"status|application|kab|when|stuck|pending|track"),
    ("privacy", r"consent|privacy|data|share|who.*(see|access)|delete|safe"),
    ("agent", r"agent|middleman|commission|broker|dalal|fee"),
]


def chat(db: Session, user: User, business: Business | None, message: str) -> dict:
    import re
    clean, found = redact(message[:1000])
    intent = next((i for i, p in INTENTS if re.search(p, clean, re.I)), "help")
    cites, invoked = [], ["orchestrator"]
    if business is None and intent not in ("agent", "help", "privacy"):
        reply = "Select a business first so I can look at its consented data."
    elif intent == "schemes":
        invoked.append("Scheme Navigator")
        elig = context(db, business)["eligibility"]
        good = [e for e in elig if e["status"] != "ineligible"][:4]
        lines = [f"• {e['short']} — {e['status']}: {e['benefit']}" for e in good]
        cites = [c for e in good for c in e["citations"][:1]]
        reply = "Here is what you can apply for:\n" + "\n".join(lines) + "\nEach rule is cited — tap a scheme for the clause."
    elif intent == "risk":
        invoked += ["Cash-flow Analyst", "Risk Assessor"]
        rk = context(db, business)["risk"]
        if not rk:
            reply = "I need your consented UPI statement before I can compute a score."
        else:
            reply = (f"Credit-readiness score {rk['score']} (band {rk['band']}, PD {rk['pd'] * 100:.1f}%). "
                     f"Helping you: {', '.join(rk['strengths'][:3])}. Holding you back: {', '.join(rk['reason_codes'][:3]) or 'nothing major'}."
                     + (f" Quick win: {rk['suggestions'][0]['action']} → score {rk['suggestions'][0]['new_score']}." if rk["suggestions"] else ""))
    elif intent == "documents":
        invoked.append("Document Agent")
        d = context(db, business)["documents"]
        miss = [i["label"] for i in d["items"] if i["status"] == "missing"]
        fetch = [i["label"] for i in d["items"] if i["status"] == "fetchable"]
        reply = (f"You need {d['stats']['required']} documents (not ~18). Upload: {', '.join(miss) or 'nothing'}. "
                 f"I can fetch with your consent: {', '.join(fetch) or 'nothing'}.")
    elif intent == "savings":
        invoked.append("Cash-flow Analyst")
        c = context(db, business)["cash"]
        s = c["summary"] if c else None
        reply = (f"You repay ~₹{s['informal_monthly_repayment']:,}/month to an informal lender. Moving ~₹{s['informal_principal_estimate']:,} "
                 f"to a scheme loan (~11% vs ~30%) saves about ₹{s['annual_interest_saving']:,} a year." if s and s["informal_monthly_repayment"]
                 else "I don't see moneylender repayments in your UPI data. A scheme loan at ~9–12% is far cheaper than 24–36% informal credit.")
    elif intent == "status":
        invoked.append("Application Drafter")
        apps = db.query(Application).filter(Application.business_id == business.id).all()
        reply = "\n".join(f"• {a.ref} {SCHEME_INDEX[a.scheme_id]['short']} {_inr(a.amount)} → {a.status.replace('_', ' ')}"
                          + (f" — {appl.stall_info(a)['nudge']}" if appl.stall_info(a) else "") for a in apps) or "No applications yet."
    elif intent == "privacy":
        invoked.append("Consent Guardian")
        reply = ("Your data is encrypted with a key unique to you (AES-256-GCM). Nobody — not a bank, agent or scheme office — "
                 "can see it without a consent you grant for a specific purpose and time, and you can revoke it anytime "
                 "from the Consent Vault. Every access is logged and visible to you. 'Erase my data' destroys your key.")
    elif intent == "agent":
        reply = ("ARTHA does the agent's job — finding schemes, assembling documents, following up — for free. "
                 "Agents typically charge 10–15% of the loan; on ₹3 lakh that is ₹30,000–45,000 you keep.")
    else:
        reply = ("Ask me: 'Which schemes am I eligible for?', 'Why is my score low?', 'What documents do I need?', "
                 "'How much will I save vs the moneylender?', 'Where is my application stuck?', 'Who can see my data?'")
    audit.record(db, user, "agents.chat", business.id if business else None, {"intent": intent, "pii_redacted": found})
    return {"reply": reply, "intent": intent, "agents_invoked": invoked, "citations": cites, "redacted": found,
            "sanitised_input": clean}
