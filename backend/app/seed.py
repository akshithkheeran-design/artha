"""Demo data: synthetic businesses, consents, UPI statements, applications and illustrative field interviews."""
import secrets

from sqlalchemy.orm import Session

from . import audit, consent, workflows
from .agents import applications as appl
from .agents import cashflow
from .crypto import encrypt_bytes, encrypt_json, new_wrapped_dek, sha256_hex
from .models import Business, CashflowDataset, Document, FieldInterview, User
from .routers.business import REGION_OF
from .security import hash_password
from .vault import owner_dek, write_profile

DEMO_PASSWORD = "Artha@Demo2026"
BC_ORG = "Jan Seva BC Network"
BANK = "Navodaya Bank · Tiruppur Branch"
DIC = "District Industries Centre · PMEGP Cell"
STAFF = [
    ("bc@artha.demo", "agent", "Suresh (Business Correspondent)", BC_ORG),
    ("manager@artha.demo", "lender", "R. Krishnan (Branch Manager)", BANK),
    ("dic@artha.demo", "dic", "A. Das (DIC Officer)", DIC),
    ("auditor@artha.demo", "auditor", "Model Risk & Fairness Office", "ARTHA Governance"),
]
# email, owner, business, sector, activity, state, district, area, lat, lng, years, emp, need, purpose, base, profile, cash-kw
B = [
    ("lakshmi@artha.demo", "Lakshmi S.", "Lakshmi Tailoring Works", "tailoring", "manufacturing", "Tamil Nadu", "Tiruppur",
     "urban", 11.108, 77.341, 6, 3, 300000, "machinery", 62000,
     dict(gender="female", social_category="obc", age=38, education="10th", is_new_unit=False, is_first_venture=False,
          prior_default=False, artisan_trade="tailor", prior_similar_scheme_loan_5y=False, govt_employee_in_family=False,
          pan="ABCPL1234K", phone="9876543210", aadhaar_last4="4821", udyam_number="UDYAM-TN-33-0012345"),
     dict(informal=6000, cv=0.15, payers=45)),
    ("ravi@artha.demo", "Ravi Patil", "Patil Steel Fabricators", "fabrication", "manufacturing", "Maharashtra", "Pune",
     "urban", 18.52, 73.856, 4, 6, 800000, "machinery", 180000,
     dict(gender="male", social_category="general", age=42, education="12th", is_new_unit=False, is_first_venture=False,
          prior_default=False, pan="BCDPP2345L", phone="9822012345", udyam_number="UDYAM-MH-26-0045678",
          aadhaar_last4="1192", artisan_trade="blacksmith", prior_similar_scheme_loan_5y=True,
          prior_similar_loan_repaid=False), dict(emi=9000, cv=0.25, payers=18, top_share=0.35)),
    ("meena@artha.demo", "Meena Behera", "Maa Tarini Mahila SHG Foods", "food_processing", "manufacturing", "Odisha",
     "Khordha", "rural", 20.18, 85.62, 3, 12, 500000, "working_capital", 90000,
     dict(gender="female", social_category="sc", age=35, education="8th_pass", is_shg=True, shg_months_active=30,
          shg_books_maintained=True, prior_default=False, is_new_unit=False, phone="9437011122"),
     dict(cv=0.3, payers=60)),
    ("gurpreet@artha.demo", "Gurpreet Singh", "Gurpreet Dairy Farm", "dairy", "agri_allied", "Punjab", "Ludhiana",
     "rural", 30.901, 75.857, 8, 2, 150000, "livestock", 70000,
     dict(gender="male", social_category="general", age=46, education="10th", prior_default=False, is_new_unit=False,
          phone="9815012345"), dict(cv=0.12, payers=25, informal=3000)),
]
EXTRA = [
    ("Anjali Boutique", "tailoring", "manufacturing", "Uttar Pradesh", "Varanasi", "urban", 25.317, 82.973, 2, 2, 150000, 38000, "female", "general"),
    ("Brahmaputra Bamboo Crafts", "handicraft", "manufacturing", "Assam", "Kamrup", "rural", 26.144, 91.736, 5, 4, 400000, 45000, "female", "st"),
    ("Shree Ganesh Welding", "fabrication", "manufacturing", "Gujarat", "Rajkot", "urban", 22.303, 70.802, 9, 5, 900000, 210000, "male", "obc"),
    ("Kaveri Milk Collective", "dairy", "agri_allied", "Karnataka", "Mandya", "rural", 12.524, 76.895, 6, 8, 600000, 150000, "female", "general"),
    ("Imphal Handloom House", "handicraft", "manufacturing", "Manipur", "Imphal East", "urban", 24.817, 93.937, 3, 3, 250000, 32000, "female", "st"),
    ("Rajput Kirana Store", "retail", "trading", "Rajasthan", "Jaipur", "urban", 26.912, 75.787, 11, 2, 200000, 95000, "male", "general"),
    ("Bastar Forest Produce SHG", "food_processing", "manufacturing", "Chhattisgarh", "Bastar", "rural", 19.107, 81.953, 2, 15, 300000, 40000, "female", "st"),
    ("Kochi Mobile Repairs", "services", "services", "Kerala", "Ernakulam", "urban", 9.98, 76.28, 4, 2, 120000, 55000, "male", "minority"),
    ("Moradabad Brass Works", "handicraft", "manufacturing", "Uttar Pradesh", "Moradabad", "urban", 28.838, 78.773, 14, 9, 1500000, 260000, "male", "minority"),
    ("Sundarban Fish Dryers", "food_processing", "manufacturing", "West Bengal", "South 24 Parganas", "rural", 22.16, 88.43, 5, 6, 350000, 60000, "male", "sc"),
    ("Indore Namkeen Udyog", "food_processing", "manufacturing", "Madhya Pradesh", "Indore", "urban", 22.719, 75.857, 1, 4, 1200000, 75000, "female", "general"),
    ("Patna Tailor Hub", "tailoring", "manufacturing", "Bihar", "Patna", "urban", 25.594, 85.137, 7, 4, 250000, 48000, "male", "obc"),
    ("Warangal Steel Grills", "fabrication", "manufacturing", "Telangana", "Warangal", "urban", 17.968, 79.594, 3, 3, 500000, 85000, "male", "sc"),
    ("Anand Dairy Unit", "dairy", "agri_allied", "Gujarat", "Anand", "rural", 22.556, 72.951, 10, 3, 200000, 90000, "female", "obc"),
]
TINY_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


def _user(db, email, role, name, org=None, password=None):
    u = User(email=email, password_hash=hash_password(password or secrets.token_urlsafe(18)), role=role,
             display_name=name, org=org)
    db.add(u)
    db.flush()
    u.dek_wrapped = new_wrapped_dek(u.id)
    return u


def _business(db, owner, name, sector, act, state, district, area, lat, lng, years, emp, need, purpose, profile):
    b = Business(owner_id=owner.id, name=name, sector=sector, activity_type=act, state=state, district=district,
                 region=REGION_OF.get(state, "central"), area=area, lat=lat, lng=lng, years_in_operation=years,
                 employees=emp, loan_need=need, loan_purpose=purpose)
    db.add(b)
    db.flush()
    db.refresh(b)
    write_profile(b, {"owner_name": owner.display_name, **profile})
    return b


def _onboard(db, owner, b, base, seed, **kw):
    consent.grant(db, owner, b, "platform", consent.PLATFORM_ORG, "cashflow_analysis",
                  ["upi_transactions", "cashflow_summary", "risk_report"], 180, commit=False)
    consent.grant(db, owner, b, "platform", consent.PLATFORM_ORG, "eligibility_check", ["eligibility", "profile"],
                  180, commit=False)
    c = consent.find_active(db, b.id, "platform", consent.PLATFORM_ORG, "upi_transactions")
    tx = cashflow.synthetic_upi(seed, base, business_id=b.id, **kw)
    ds = CashflowDataset(business_id=b.id, consent_id=c.id, source="account_aggregator_simulated", row_count=len(tx),
                         sha256=sha256_hex(repr(tx).encode()), data_enc=b"")
    db.add(ds)
    db.flush()
    ds.data_enc = encrypt_json(owner_dek(b), tx, f"cashflow:{b.id}:{ds.id}")
    audit.record(db, owner, "cashflow.ingested", b.id, {"source": ds.source, "rows": len(tx)}, commit=False)


def _doc(db, owner, b, doc_type, source="upload"):
    d = Document(business_id=b.id, doc_type=doc_type, filename=f"{doc_type}.pdf", mime="application/pdf",
                 size=len(TINY_PDF), sha256=sha256_hex(TINY_PDF), source=source, uploaded_by=owner.id)
    db.add(d)
    db.flush()
    d.content_enc = encrypt_bytes(owner_dek(b), TINY_PDF, f"doc:{b.id}:{d.id}")


def _app(db, actor, owner, b, scheme, lender, amount, path, age_days):
    a = workflows.create(db, actor, b, scheme, lender, amount)
    a.created_at = appl.days_ago(age_days)
    if path:
        workflows.approve(db, owner, b, a, list(workflows.DEFAULT_SHARE), 120)
        a.timeline[-1]["at"] = appl.days_ago(age_days - 1).isoformat()
        for i, (st, note) in enumerate(path[1:], start=2):
            a.status = st
            a.timeline = a.timeline + [appl.event(st, note, lender, appl.days_ago(max(0, age_days - i * 3)))]
        a.updated_at = appl.days_ago(max(0.0, age_days - (len(path)) * 3))
        if a.status == "submitted":
            a.updated_at = appl.days_ago(age_days - 1)
    else:
        a.updated_at = appl.days_ago(age_days)
    return a


def seed(db: Session) -> None:
    if db.query(User).first():
        return
    staff = {role: _user(db, e, role, n, org, DEMO_PASSWORD) for e, role, n, org in STAFF}
    owners = {}
    for i, (email, oname, bname, sector, act, state, dist, area, lat, lng, yrs, emp, need, purpose, base, prof, kw) in enumerate(B):
        o = _user(db, email, "entrepreneur", oname, password=DEMO_PASSWORD)
        b = _business(db, o, bname, sector, act, state, dist, area, lat, lng, yrs, emp, need, purpose, prof)
        _onboard(db, o, b, base, 100 + i, **kw)
        owners[email] = (o, b)
    for i, (name, sector, act, state, dist, area, lat, lng, yrs, emp, need, base, g, cat) in enumerate(EXTRA):
        o = _user(db, f"owner{i}@artha.demo", "entrepreneur", f"Owner {i + 1}")
        prof = dict(gender=g, social_category=cat, age=30 + i, education="10th", prior_default=False,
                    is_new_unit=yrs < 2, is_first_venture=yrs < 2, is_shg="SHG" in name,
                    shg_months_active=24 if "SHG" in name else None, shg_books_maintained="SHG" in name,
                    artisan_trade="tailor" if sector == "tailoring" else None,
                    prior_similar_scheme_loan_5y=False, govt_employee_in_family=False)
        b = _business(db, o, name, sector, act, state, dist, area, lat, lng, yrs, emp, need,
                      "new_unit" if yrs < 2 else "working_capital", prof)
        _onboard(db, o, b, base, 200 + i, cv=0.12 + (i % 5) * 0.12, payers=8 + i * 3, top_share=0.1 + (i % 4) * 0.14,
                 informal=(base * 0.16 if i % 3 == 0 else 0), months=4 + (i * 5) % 13)
        owners[o.email] = (o, b)

    lo, lb = owners["lakshmi@artha.demo"]
    for d in ("kyc_aadhaar", "pan", "photo", "business_proof"):
        _doc(db, lo, lb, d, "digilocker" if d in ("kyc_aadhaar", "pan") else "upload")
    consent.grant(db, lo, lb, "agent", BC_ORG, "assisted_onboarding", ["profile", "eligibility", "documents",
                                                                         "cashflow_summary"], 60, commit=False)
    _app(db, lo, lo, lb, "mudra", BANK, 250000, [("submitted", "")], 10)
    _app(db, staff["agent"], lo, lb, "vishwakarma", BANK, 100000, None, 1)

    ro, rb = owners["ravi@artha.demo"]
    for d in ("kyc_aadhaar", "pan", "udyam", "photo", "business_proof", "quotation"):
        _doc(db, ro, rb, d)
    _app(db, ro, ro, rb, "cgtmse", BANK, 800000, [("submitted", ""), ("under_review", "File picked up by credit officer")], 9)

    mo, mb = owners["meena@artha.demo"]
    consent.grant(db, mo, mb, "agent", BC_ORG, "assisted_onboarding", ["profile", "eligibility", "documents"], 90,
                  commit=False)
    _app(db, staff["agent"], mo, mb, "nrlm", BANK, 500000,
         [("submitted", ""), ("docs_requested", "Please upload SHG resolution and grading sheet")], 18)

    go, gb = owners["gurpreet@artha.demo"]
    _doc(db, go, gb, "kyc_aadhaar")
    _app(db, go, go, gb, "kcc_ah", BANK, 150000,
         [("submitted", ""), ("under_review", "Field visit scheduled"), ("sanctioned", "Sanctioned ₹1.5 lakh KCC limit")], 25)

    plan = [("Rajput Kirana Store", "mudra", BANK, 200000, [("submitted", ""), ("under_review", "")], 6),
            ("Kochi Mobile Repairs", "mudra", BANK, 120000, [("submitted", ""), ("sanctioned", "Sanctioned")], 20),
            ("Patna Tailor Hub", "mudra", BANK, 250000, [("submitted", "")], 3),
            ("Moradabad Brass Works", "cgtmse", BANK, 1500000, [("submitted", ""), ("docs_requested", "Need GST returns")], 16),
            ("Indore Namkeen Udyog", "pmegp", DIC, 1200000, [("submitted", ""), ("under_review", "Task force interview")], 12),
            ("Warangal Steel Grills", "mudra", BANK, 500000, [("submitted", ""), ("rejected", "")], 30),
            ("Anand Dairy Unit", "kcc_ah", "Kaveri Gramin Bank", 200000, [("submitted", "")], 4)]
    byname = {b.name: (o, b) for o, b in owners.values()}
    for name, sch, lender, amt, path, age in plan:
        o, b = byname[name]
        a = _app(db, o, o, b, sch, lender, amt, path, age)
        if a.status == "rejected":
            a.decision_reason = "R02"
    for d in ("kyc_aadhaar", "pan", "photo"):
        _doc(db, *byname["Patna Tailor Hub"], d)

    samples = [
        ("entrepreneur", "tailoring", "Tamil Nadu", ["mudra"], "bank_mitra", 16, "documents", 12, ["form filling", "branch visits"], ["upi", "notebook"], "conditional", [], "documents"),
        ("entrepreneur", "fabrication", "Maharashtra", ["mudra", "cgtmse"], "agent", 19, "collateral", 15, ["form filling", "contacts at branch"], ["upi", "supplier_bills"], "yes", [], "collateral"),
        ("shg", "food_processing", "Odisha", ["nrlm"], "shg", 9, "no_response", None, [], ["shg_books", "upi"], "yes", [], "no_response"),
        ("entrepreneur", "dairy", "Punjab", ["kcc_ah"], "neighbour", 12, "branch_visit", 10, ["documents"], ["milk_society_slips", "upi"], "yes", [], "time_lost"),
        ("entrepreneur", "handicraft", "Assam", [], "none", None, "none", None, [], ["notebook", "whatsapp_orders"], "conditional", [], "unaware"),
        ("bc_agent", "mixed", "Bihar", ["mudra", "pmegp", "vishwakarma"], "bank_mitra", 18, "documents", 10, ["form filling", "document collection", "follow-up"], ["upi"], "conditional", [], "documents"),
        ("branch_manager", "bank", "Tamil Nadu", ["mudra", "cgtmse", "standup"], "none", None, "documents", None, [], [], "yes", ["12m cash-flow", "KYC", "Udyam", "repayment history", "CGTMSE cover"], "documents"),
        ("branch_manager", "bank", "Gujarat", ["mudra", "pmegp"], "none", None, "documents", None, [], [], "yes", ["bank statement", "project viability", "existing loans"], "no_response"),
        ("dic_officer", "agency", "Madhya Pradesh", ["pmegp"], "none", None, "documents", None, [], [], "yes", ["project report", "EDP"], "documents"),
        ("entrepreneur", "retail", "Rajasthan", ["mudra"], "social_media", 14, "rejected", 15, ["form filling"], ["upi", "notebook"], "no", [], "rejected"),
    ]
    for (rt, sec, st, heard, frm, docs, stall, fee, services, records, share, needs, drop) in samples:
        db.add(FieldInterview(interviewer_id=staff["agent"].id, respondent_type=rt, sector=sec, state=st, is_sample=True,
                              answers={"schemes_heard": heard, "heard_from": frm, "last_loan_documents": docs,
                                       "stalled_at": stall, "agent_fee_pct": fee, "agent_services": services,
                                       "informal_records": records, "willing_to_share": share, "branch_needs": needs,
                                       "dropout_reason": drop,
                                       "cost_per_incomplete_file": 4200 if rt == "branch_manager" else None,
                                       "notes": "Illustrative sample — replace with real field interviews."}))
    audit.record(db, "system", "system.seeded", None, {"businesses": len(owners)}, commit=False)
    db.commit()
