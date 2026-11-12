"""Cash-flow agent: turns consented UPI / bank lines into explainable credit indicators."""
import csv
import io
import math
import random
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from ..crypto import blind_index

MAX_ROWS = 20_000
CATEGORY_RULES = [
    ("informal_lender", re.compile(r"byaj|vyaj|interest|sahukar|moneylender|chit|daily\s*fin|finance\s*coll", re.I)),
    ("emi", re.compile(r"\bemi\b|loan|nach|ecs", re.I)),
    ("wages", re.compile(r"salary|wage|majdoori|labour|labor", re.I)),
    ("rent", re.compile(r"rent|kiraya", re.I)),
    ("utilities", re.compile(r"electric|eb bill|power|water|gas|recharge|bill", re.I)),
    ("supplier", re.compile(r"supplier|purchase|wholesale|cloth|steel|fodder|feed|raw|stock|material", re.I)),
]
INFORMAL_RATE = 0.30   # mid-point of the 24–36% moneylender range in the problem statement
SCHEME_RATE = 0.11     # indicative formal MSME rate used for comparison only


def categorise(direction: str, note: str) -> str:
    for cat, pat in CATEGORY_RULES:
        if pat.search(note or ""):
            return cat
    return "sales" if direction == "CR" else "other"


def parse_csv(raw: bytes, business_id: int) -> list[dict]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "File must be UTF-8 CSV")
    reader = csv.DictReader(io.StringIO(text))
    cols = {c.strip().lower() for c in (reader.fieldnames or [])}
    need = {"date", "amount", "type"}
    if not need <= cols:
        raise HTTPException(422, "CSV needs columns: date, amount, type (CR/DR), counterparty, note")
    out = []
    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            raise HTTPException(413, f"Too many rows (max {MAX_ROWS})")
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            d = datetime.strptime(row["date"][:10], "%Y-%m-%d").date()
            amt = float(row["amount"].replace(",", ""))
        except ValueError:
            raise HTTPException(422, f"Row {i + 2}: invalid date (YYYY-MM-DD) or amount")
        direction = row["type"].upper()[:2]
        if direction not in ("CR", "DR") or not (0 < amt < 1e8):
            raise HTTPException(422, f"Row {i + 2}: type must be CR/DR and amount positive")
        note = row.get("note", "")[:80]
        out.append({"date": d.isoformat(), "amount": round(amt, 2), "type": direction,
                    "cp": blind_index(row.get("counterparty", "unknown"), f"b{business_id}"),
                    "cat": categorise(direction, note)})
    if len(out) < 10:
        raise HTTPException(422, "Need at least 10 transactions to analyse")
    return out


def synthetic_upi(seed: int, base: float, cv: float = 0.2, months: int = 12, payers: int = 40,
                  top_share: float = 0.15, margin: float = 0.25, emi: float = 0, informal: float = 0,
                  trend: float = 0.01, season: list[float] | None = None, business_id: int = 0,
                  end: date | None = None) -> list[dict]:
    rng = random.Random(seed)
    end = end or date.today().replace(day=1) - timedelta(days=1)
    season = season or [1.0] * 12
    txns = []
    payer_ids = [f"payer{i}@upi" for i in range(payers)]
    starts = []
    cur = end.replace(day=1)
    for _ in range(months):
        starts.append(cur)
        cur = (cur - timedelta(days=1)).replace(day=1)
    starts.reverse()
    for idx, first in enumerate(starts):
        days = ((first + timedelta(days=32)).replace(day=1) - first).days
        if first == end.replace(day=1):
            days = end.day
        target = base * (1 + trend) ** (idx - months + 1) * season[first.month - 1] * max(0.2, rng.gauss(1, cv))
        n = max(8, int(target / max(150.0, base / 90)))
        weights = [top_share * payers] + [1.0] * (payers - 1)
        for _ in range(n):
            p = rng.choices(payer_ids, weights=weights)[0]
            amt = max(20, rng.lognormvariate(math.log(target / n), 0.5))
            d = first + timedelta(days=rng.randrange(days))
            txns.append({"date": d.isoformat(), "amount": round(amt, 0), "type": "CR",
                         "cp": blind_index(p, f"b{business_id}"), "cat": "sales"})
        spend = target * (1 - margin)
        for cat, share in (("supplier", 0.6), ("wages", 0.2), ("rent", 0.1), ("utilities", 0.1)):
            k = 4 if cat == "supplier" else 1
            for _ in range(k):
                d = first + timedelta(days=rng.randrange(days))
                txns.append({"date": d.isoformat(), "amount": round(spend * share / k, 0), "type": "DR",
                             "cp": blind_index(f"{cat}{rng.randrange(3)}", f"b{business_id}"), "cat": cat})
        if emi:
            txns.append({"date": first.replace(day=5).isoformat(), "amount": emi, "type": "DR",
                         "cp": blind_index("bank-emi", f"b{business_id}"), "cat": "emi"})
        if informal:
            for wk in range(4):
                d = first + timedelta(days=min(days - 1, wk * 7 + 2))
                txns.append({"date": d.isoformat(), "amount": round(informal / 4, 0), "type": "DR",
                             "cp": blind_index("sahukar", f"b{business_id}"), "cat": "informal_lender"})
    txns.sort(key=lambda t: t["date"])
    return txns


def _pv(payment: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    return payment * (1 - (1 + r) ** -months) / r


def analyse(txns: list[dict], years_in_operation: float = 0) -> dict:
    by_month = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0, "obligations": 0.0, "informal": 0.0,
                                    "payers": set(), "credit_days": set()})
    payer_totals = defaultdict(float)
    for t in txns:
        m = t["date"][:7]
        b = by_month[m]
        if t["type"] == "CR":
            b["inflow"] += t["amount"]
            b["payers"].add(t["cp"])
            b["credit_days"].add(t["date"])
            payer_totals[t["cp"]] += t["amount"]
        else:
            b["outflow"] += t["amount"]
            if t["cat"] in ("emi", "informal_lender"):
                b["obligations"] += t["amount"]
            if t["cat"] == "informal_lender":
                b["informal"] += t["amount"]
    months = sorted(by_month)
    n = len(months)
    inflows = [by_month[m]["inflow"] for m in months]
    outflows = [by_month[m]["outflow"] for m in months]
    total_in = sum(inflows) or 1.0
    mean_in = total_in / max(n, 1)
    sd_in = math.sqrt(sum((x - mean_in) ** 2 for x in inflows) / max(n, 1))
    med = sorted(inflows)[n // 2] if n else 0
    xs = list(range(n))
    xbar = sum(xs) / n if n else 0
    slope = (sum((x - xbar) * (y - mean_in) for x, y in zip(xs, inflows, strict=False)) /
             (sum((x - xbar) ** 2 for x in xs) or 1))
    first_day = datetime.strptime(txns[0]["date"], "%Y-%m-%d").date()
    last_day = datetime.strptime(txns[-1]["date"], "%Y-%m-%d").date()
    span_days = (last_day - first_day).days + 1
    credit_days = set().union(*(by_month[m]["credit_days"] for m in months))
    obligations = sum(by_month[m]["obligations"] for m in months)
    informal = sum(by_month[m]["informal"] for m in months)
    surpluses = sorted(i - o + by_month[m]["obligations"] for m, i, o in zip(months, inflows, outflows, strict=False))
    stressed = surpluses[max(0, n // 4 - 1)] if n else 0
    max_emi = max(0.0, 0.5 * stressed)
    informal_monthly = informal / max(n, 1)
    informal_principal = _pv(informal_monthly, INFORMAL_RATE, 12) if informal_monthly else 0

    features = {
        "months_history": n,
        "log_inflow": math.log(max(mean_in, 1)),
        "inflow_cv": sd_in / mean_in if mean_in else 1.0,
        "surplus_ratio": (total_in - sum(outflows)) / total_in,
        "payers_per_month": sum(len(by_month[m]["payers"]) for m in months) / max(n, 1),
        "top_payer_share": max(payer_totals.values()) / total_in if payer_totals else 1.0,
        "active_day_ratio": len(credit_days) / max(span_days, 1),
        "inflow_trend": slope / mean_in if mean_in else 0.0,
        "obligation_ratio": obligations / total_in,
        "low_month_share": sum(x < 0.5 * med for x in inflows) / max(n, 1),
        "years_in_operation": float(years_in_operation or 0),
    }
    insights = []
    if features["inflow_cv"] < 0.2:
        insights.append("Steady monthly UPI inflows — low volatility is a strong repayment signal.")
    elif features["inflow_cv"] > 0.4:
        insights.append("Inflows swing a lot month to month — a seasonal repayment schedule may suit better.")
    if features["payers_per_month"] >= 20:
        insights.append(f"~{features['payers_per_month']:.0f} distinct customers pay every month — diversified demand.")
    if features["top_payer_share"] > 0.4:
        insights.append("Over 40% of income comes from one payer — concentration risk.")
    if informal_monthly:
        insights.append(f"Detected recurring repayments to an informal lender (~₹{informal_monthly:,.0f}/month). "
                        f"Refinancing at a scheme rate could save ~₹{informal_principal * (INFORMAL_RATE - SCHEME_RATE):,.0f}/year.")
    if features["inflow_trend"] > 0.02:
        insights.append(f"Revenue growing ~{features['inflow_trend'] * 100:.1f}% per month.")
    return {
        "features": {k: round(v, 4) for k, v in features.items()},
        "monthly": [{"month": m, "inflow": round(i), "outflow": round(o),
                     "obligations": round(by_month[m]["obligations"]), "payers": len(by_month[m]["payers"])}
                    for m, i, o in zip(months, inflows, outflows, strict=False)],
        "summary": {
            "avg_monthly_inflow": round(mean_in), "avg_monthly_outflow": round(sum(outflows) / max(n, 1)),
            "transactions": len(txns), "months": n, "stressed_monthly_surplus": round(stressed),
            "sustainable_emi": round(max_emi), "suggested_loan_36m": round(_pv(max_emi, SCHEME_RATE, 36)) if max_emi else 0,
            "informal_monthly_repayment": round(informal_monthly),
            "informal_principal_estimate": round(informal_principal),
            "annual_interest_saving": round(informal_principal * (INFORMAL_RATE - SCHEME_RATE)),
            "informal_rate_assumed": INFORMAL_RATE, "scheme_rate_assumed": SCHEME_RATE,
        },
        "categories": _cat_totals(txns),
        "insights": insights,
    }


def _cat_totals(txns):
    tot = defaultdict(float)
    for t in txns:
        if t["type"] == "DR":
            tot[t["cat"]] += t["amount"]
    return [{"category": k, "amount": round(v)} for k, v in sorted(tot.items(), key=lambda kv: -kv[1])]
