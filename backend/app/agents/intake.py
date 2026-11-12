"""Intake agent: turns a free-text (English / Hinglish) description into a structured draft profile."""
import re

from .schemes import VISHWAKARMA_TRADES

SECTORS = [
    ("tailoring", "manufacturing", r"tailor|silai|stitch|darzi|boutique|garment"),
    ("fabrication", "manufacturing", r"fabricat|weld|grill|gate|sheet metal|lohar|blacksmith"),
    ("dairy", "agri_allied", r"dairy|doodh|milk|cow|buffalo|bhains|cattle"),
    ("food_processing", "manufacturing", r"pickle|papad|achar|food|tiffin|catering|bakery|snack"),
    ("handicraft", "manufacturing", r"pottery|potter|craft|weav|handloom|carpent|bamboo"),
    ("retail", "trading", r"kirana|shop|store|retail|vendor|thela|stall"),
    ("services", "services", r"salon|barber|repair|mobile|beauty|laundry|washerman|transport|auto"),
]
STATES = ["andhra pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh",
          "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
          "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
          "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu and kashmir"]


def _amount(txt: str) -> int | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|l\b|k\b|thousand|hazaar|hajar|crore|cr\b)", txt, re.I)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2).lower()
    mult = 1e7 if unit.startswith("cr") else 1e5 if unit.startswith("la") or unit == "l" else 1e3
    return int(n * mult)


def parse(text: str) -> dict:
    t = text.lower()
    f: dict = {}
    for sector, act, pat in SECTORS:
        if re.search(pat, t):
            f["sector"], f["activity_type"] = sector, act
            break
    if m := re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|saal|sal)\b", t):
        f["years_in_operation"] = float(m.group(1))
    need = re.search(r"(?:need|want|chahiye|loan|require)[^.]*?(\d+(?:\.\d+)?\s*(?:lakh|lac|k|thousand|hazaar|crore))", t)
    if need:
        f["loan_need"] = _amount(need.group(1))
    upi = re.search(r"(?:upi|sales|income|kamai|earn)[^.]*?(\d+(?:\.\d+)?\s*(?:lakh|lac|k|thousand|hazaar))", t)
    if upi:
        f["monthly_upi_inflow"] = _amount(upi.group(1))
    if re.search(r"\b(woman|women|female|mahila|lady|she|her)\b", t):
        f["gender"] = "female"
    elif re.search(r"\b(man|male|he|his)\b", t):
        f["gender"] = "male"
    if re.search(r"\b(sc|scheduled caste|dalit)\b", t):
        f["social_category"] = "sc"
    elif re.search(r"\b(st|scheduled tribe|adivasi|tribal)\b", t):
        f["social_category"] = "st"
    elif re.search(r"\bobc\b", t):
        f["social_category"] = "obc"
    if re.search(r"\b(shg|self[- ]help group|samooh|sangha)\b", t):
        f["is_shg"] = True
    if re.search(r"\b(start|new unit|naya|planning to open|want to open)\b", t):
        f["is_new_unit"] = True
    elif f.get("years_in_operation"):
        f["is_new_unit"] = False
    if re.search(r"village|gaon|rural|gram", t):
        f["area"] = "rural"
    elif re.search(r"city|town|urban|shahar", t):
        f["area"] = "urban"
    if re.search(r"machine|equipment|tools", t):
        f["loan_purpose"] = "machinery"
    elif re.search(r"cow|buffalo|cattle|livestock", t):
        f["loan_purpose"] = "livestock"
    elif re.search(r"stock|raw material|working capital|inventory", t):
        f["loan_purpose"] = "working_capital"
    if re.search(r"moneylender|sahukar|byaj|interest.*(daily|weekly)|36%|30%", t):
        f["uses_moneylender"] = True
    for trade in VISHWAKARMA_TRADES:
        if trade.split("/")[0] in t or (trade == "tailor" and f.get("sector") == "tailoring"):
            f["artisan_trade"] = trade
            break
    if re.search(r"street|thela|footpath|hawker|vendor", t):
        f["street_vendor"] = True
    for s in STATES:
        if s in t:
            f["state"] = s.title()
            break
    if m := re.search(r"\b(?:in|at|from|near)\s+([A-Z][a-zA-Z]+)", text):
        if m.group(1).lower() not in STATES:
            f["district"] = m.group(1)
    if m := re.search(r"(\d+)\s*(?:workers|employees|staff|karigar|people)", t):
        f["employees"] = int(m.group(1))
    questions = []
    asks = [("sector", "What does your business make or sell?"),
            ("years_in_operation", "How many years has the business been running?"),
            ("loan_need", "How much money do you need, and for what?"),
            ("gender", "Is the business owned by a woman? (unlocks Stand-Up India, higher PMEGP subsidy)"),
            ("social_category", "Do you belong to SC / ST / OBC / minority? (optional — only used for scheme rules)"),
            ("area", "Is the unit in a village or a town?"),
            ("state", "Which state and district?")]
    for k, q in asks:
        if k not in f:
            questions.append(q)
    return {"extracted": f, "follow_up_questions": questions[:4],
            "confidence": round(min(1.0, len(f) / 9), 2)}
