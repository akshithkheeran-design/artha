"""Scheme Eligibility agent: deterministic rules, each with the citation it derives from."""
from .schemes import C, SCHEME_INDEX, SCHEMES, SPECIAL_CATEGORIES, VISHWAKARMA_TRADES

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"


def _r(rule: str, status: str, detail: str, citation: dict) -> dict:
    return {"rule": rule, "status": status, "detail": detail, "citation": citation}


def _bool(p: dict, key: str):
    v = p.get(key)
    return None if v is None or v == "" else bool(v)


def _inr(n: float) -> str:
    n = int(round(n))
    if n >= 10_000_000:
        return f"₹{n / 10_000_000:.2f} crore"
    if n >= 100_000:
        return f"₹{n / 100_000:.2f} lakh"
    return f"₹{n:,}"


def _mudra(b, p):
    need = b.loan_need or 0
    out = [
        _r("Non-farm income-generating activity (manufacturing, trading, services or agri-allied such as dairy)",
           PASS if b.activity_type in {"manufacturing", "trading", "services", "agri_allied"} else FAIL,
           f"Activity: {b.activity_type.replace('_', ' ')}", C["mudra_faq"]),
        _r("Not a defaulter to any bank / financial institution",
           UNKNOWN if _bool(p, "prior_default") is None else (FAIL if p.get("prior_default") else PASS),
           "Self-declared; lender verifies with credit bureau", C["mudra_faq"]),
    ]
    tp = bool(p.get("prior_mudra_tarun_repaid"))
    cap = 2_000_000 if tp else 1_000_000
    out.append(_r("Loan amount within MUDRA limit (₹10 lakh; ₹20 lakh Tarun Plus after repaying a Tarun loan)",
                  PASS if 0 < need <= cap else FAIL, f"Requested {_inr(need)}; your cap {_inr(cap)}",
                  C["mudra_tp"] if tp else C["mudra"]))
    cat = ("Shishu" if need <= 50_000 else "Kishore" if need <= 500_000 else "Tarun" if need <= 1_000_000
           else "Tarun Plus")
    return out, min(need, cap), f"Category: {cat}"


def _pmegp(b, p):
    service = b.activity_type in {"services", "trading"}
    limit = 2_000_000 if service else 5_000_000
    need = b.loan_need or 0
    age = p.get("age")
    edu = p.get("education")
    new = _bool(p, "is_new_unit")
    out = [
        _r("Age 18 years or above", UNKNOWN if age is None else (PASS if age >= 18 else FAIL),
           f"Age: {age if age is not None else 'not provided'}", C["pmegp"]),
        _r("Only NEW projects (existing units / units that already availed Govt subsidy are not eligible)",
           UNKNOWN if new is None else (PASS if new and not p.get("availed_govt_subsidy") else FAIL),
           "New unit" if new else "Existing unit — PMEGP first loan is for new projects only", C["pmegp"]),
        _r(f"Project cost within ceiling ({_inr(limit)} for {'service' if service else 'manufacturing'})",
           PASS if 0 < need <= limit else FAIL, f"Project cost {_inr(need)}", C["pmegp"]),
    ]
    edu_needed = need > (500_000 if service else 1_000_000)
    if edu_needed:
        ok = edu in {"8th_pass", "10th", "12th", "graduate"}
        out.append(_r("At least VIII standard pass (projects above ₹10 lakh manufacturing / ₹5 lakh service)",
                      UNKNOWN if not edu else (PASS if ok else FAIL), f"Education: {edu or 'not provided'}",
                      C["pmegp"]))
    special = (p.get("social_category") in SPECIAL_CATEGORIES or p.get("gender") in {"female", "transgender"}
               or p.get("ex_serviceman") or p.get("differently_abled") or b.region == "northeast")
    rate = (0.35 if b.area == "rural" else 0.25) if special else (0.25 if b.area == "rural" else 0.15)
    note = f"Indicative margin-money subsidy {int(rate * 100)}% ≈ {_inr(need * rate)}"
    out.append(_r("Margin-money subsidy rate by category and location", PASS, note, C["pmegp_fin"]))
    return out, min(need, limit), note


def _standup(b, p):
    need = b.loan_need or 0
    sc_st = p.get("social_category") in {"sc", "st"}
    woman = p.get("gender") == "female"
    first = _bool(p, "is_first_venture")
    if first is None:
        first = _bool(p, "is_new_unit")
    out = [
        _r("Entrepreneur is SC/ST and/or a woman (≥51% shareholding if not an individual)",
           PASS if (sc_st or woman) else (UNKNOWN if not p.get("gender") else FAIL),
           "Qualifies" if (sc_st or woman) else "Scheme is reserved for SC/ST and women entrepreneurs", C["sui"]),
        _r("Greenfield (first-time) enterprise in manufacturing, services, trading or agri-allied",
           UNKNOWN if first is None else (PASS if first else FAIL),
           "First venture" if first else "Existing enterprise — not greenfield", C["sui"]),
        _r("Loan between ₹10 lakh and ₹1 crore", PASS if 1_000_000 <= need <= 10_000_000 else FAIL,
           f"Requested {_inr(need)}", C["sui"]),
        _r("Not in default to any bank / financial institution",
           UNKNOWN if _bool(p, "prior_default") is None else (FAIL if p.get("prior_default") else PASS),
           "Self-declared", C["sui"]),
        _r("Age 18 years or above", UNKNOWN if p.get("age") is None else (PASS if p["age"] >= 18 else FAIL),
           f"Age: {p.get('age')}", C["sui"]),
    ]
    return out, need, "Composite loan (term + working capital)"


def _cgtmse(b, p):
    has_udyam = bool(p.get("udyam_number"))
    out = [
        _r("Micro or Small Enterprise in manufacturing or services (incl. retail trade)",
           FAIL if p.get("is_shg") else (UNKNOWN if b.activity_type == "agri_allied" else PASS),
           "SHG lending is covered under DAY-NRLM instead" if p.get("is_shg") else
           ("Agri-allied activity — confirm coverage with lender" if b.activity_type == "agri_allied"
            else f"Activity: {b.activity_type}"), C["cgtmse"]),
        _r("Udyam Registration (free, online)", PASS if has_udyam else UNKNOWN,
           "Registered" if has_udyam else "Register on udyamregistration.gov.in — ARTHA can pre-fill it",
           C["udyam"]),
        _r("Collateral-free credit from a member lending institution, within the ₹10 crore cover",
           PASS if (b.loan_need or 0) <= 100_000_000 else FAIL, "Lender applies for the guarantee", C["cgtmse_b25"]),
    ]
    return out, b.loan_need, "Removes the collateral requirement — ask the branch to cover the loan under CGTMSE"


def _vishwakarma(b, p):
    trade = (p.get("artisan_trade") or "").lower()
    in_trade = trade in VISHWAKARMA_TRADES
    prior = _bool(p, "prior_similar_scheme_loan_5y")
    repaid = bool(p.get("prior_similar_loan_repaid"))
    out = [
        _r("Artisan / craftsperson working with hands & tools in one of the 18 family-based trades",
           PASS if in_trade else (UNKNOWN if not trade else FAIL),
           f"Trade: {trade or 'not provided'}", C["vishwakarma"]),
        _r("Minimum age 18 years", UNKNOWN if p.get("age") is None else (PASS if p["age"] >= 18 else FAIL),
           f"Age: {p.get('age')}", C["vishwakarma"]),
        _r("No self-employment loan under PMEGP / PM SVANidhi / MUDRA in last 5 years (unless fully repaid)",
           UNKNOWN if prior is None else (PASS if (not prior or repaid) else FAIL),
           "No recent similar loan" if not prior else ("Previous loan repaid" if repaid else "Outstanding similar loan"),
           C["vishwakarma"]),
        _r("No family member in Government service", UNKNOWN if _bool(p, "govt_employee_in_family") is None
           else (FAIL if p.get("govt_employee_in_family") else PASS), "Self-declared", C["vishwakarma"]),
    ]
    return out, min(b.loan_need or 0, 100_000) or 100_000, "First tranche ₹1 lakh (18 months), then ₹2 lakh at 5%"


def _svanidhi(b, p):
    vendor = bool(p.get("street_vendor"))
    out = [
        _r("Street vendor in an urban / peri-urban area", PASS if (vendor and b.area == "urban") else FAIL,
           "Street vendor" if vendor else "Not a street-vending business", C["svanidhi"]),
        _r("Certificate of Vending / ID from ULB, or Letter of Recommendation",
           PASS if p.get("has_vending_certificate") else (UNKNOWN if vendor else FAIL),
           "Available" if p.get("has_vending_certificate") else "Can be requested from the ULB / TVC",
           C["svanidhi"]),
    ]
    return out, 15_000, "Tranche 1 ₹15,000 → ₹25,000 → ₹50,000"


def _nrlm(b, p):
    shg = bool(p.get("is_shg"))
    months = p.get("shg_months_active") or 0
    out = [
        _r("Borrower is a Self-Help Group", PASS if shg else FAIL, "SHG" if shg else "Individual enterprise",
           C["nrlm_portal"]),
        _r("SHG active for at least 6 months as per its books", PASS if months >= 6 else (FAIL if shg else UNKNOWN),
           f"Active {months} months", C["nrlm"]),
        _r("Regular savings, internal lending and books maintained (Panchasutra)",
           PASS if p.get("shg_books_maintained") else UNKNOWN, "Grading done at branch", C["nrlm"]),
        _r("Collateral-free up to ₹20 lakh", PASS if (b.loan_need or 0) <= 2_000_000 else FAIL,
           f"Requested {_inr(b.loan_need or 0)}", C["nrlm"]),
    ]
    return out, min(b.loan_need or 0, 2_000_000), "Interest subvention available for women SHGs"


def _kcc(b, p):
    dairy = b.sector == "dairy" or b.activity_type == "agri_allied"
    need = b.loan_need or 0
    out = [
        _r("Animal husbandry / dairy activity", PASS if dairy else FAIL, f"Sector: {b.sector}", C["kcc_dahd"]),
        _r("Collateral-free up to ₹2 lakh", PASS if need <= 200_000 else UNKNOWN,
           "Within limit" if need <= 200_000 else "Above ₹2 lakh the bank may ask for security", C["kcc_ah"]),
    ]
    return out, min(need, 300_000), "Short-term working capital for feed, fodder, veterinary costs"


RULES = {"mudra": _mudra, "pmegp": _pmegp, "standup": _standup, "cgtmse": _cgtmse, "vishwakarma": _vishwakarma,
         "svanidhi": _svanidhi, "nrlm": _nrlm, "kcc_ah": _kcc}


def evaluate(business, profile: dict) -> list[dict]:
    results = []
    for s in SCHEMES:
        checks, amount, note = RULES[s["id"]](business, profile)
        fails = [c for c in checks if c["status"] == FAIL]
        unknowns = [c for c in checks if c["status"] == UNKNOWN]
        status = "ineligible" if fails else ("likely" if unknowns else "eligible")
        passed = sum(c["status"] == PASS for c in checks)
        results.append({
            "scheme_id": s["id"], "name": s["name"], "short": s["short"], "agency": s["agency"],
            "status": status, "match": round(passed / len(checks), 2),
            "indicative_amount": int(amount or 0), "note": note, "benefit": s["benefit"],
            "typical_rate": s["typical_rate"], "checks": checks, "citations": s["citations"],
            "documents": s["documents"],
            "next_step": ("Missing information: " + "; ".join(c["rule"] for c in unknowns)) if status == "likely"
            else ("Not applicable: " + fails[0]["detail"]) if fails else "Ready to draft an application",
        })
    order = {"eligible": 0, "likely": 1, "ineligible": 2}
    results.sort(key=lambda r: (order[r["status"]], -r["match"]))
    return results


def scheme(sid: str) -> dict:
    return SCHEME_INDEX[sid]
