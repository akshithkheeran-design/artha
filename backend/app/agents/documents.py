"""Document agent: collapses 15–20 scheme documents into one consent-driven core pack."""
from .schemes import DOCUMENTS, SCHEME_INDEX

TRADITIONAL_DOC_COUNT = 18  # typical MSME loan file per the problem statement (15–20)


def checklist(business, profile: dict, eligibility: list[dict], uploaded: list, has_cashflow: bool,
              target_scheme: str | None = None) -> dict:
    schemes = [target_scheme] if target_scheme else [e["scheme_id"] for e in eligibility
                                                     if e["status"] in ("eligible", "likely")][:3]
    needed: dict[str, set] = {}
    for d, meta in DOCUMENTS.items():
        if meta["core"]:
            needed[d] = {"core"}
    for sid in schemes:
        for d in SCHEME_INDEX[sid]["documents"]:
            needed.setdefault(d, set()).add(SCHEME_INDEX[sid]["short"])
    cat = profile.get("social_category")
    if cat not in ("sc", "st", "obc"):
        needed.pop("caste_cert", None)
    if business.area != "rural":
        needed.pop("rural_cert", None)
    if business.loan_purpose == "working_capital":
        needed.pop("quotation", None)
    up = {u.doc_type: u for u in uploaded}
    items = []
    for d, used_by in needed.items():
        meta = DOCUMENTS[d]
        if d in up:
            status = "uploaded"
        elif d == "bank_statement" and has_cashflow:
            status = "fetched"
        elif d == "udyam" and profile.get("udyam_number"):
            status = "fetched"
        elif d == "project_report":
            status = "auto"
        elif d == "edp_cert":
            status = "after_sanction"
        elif meta["auto"] in ("digilocker", "aa"):
            status = "fetchable"
        else:
            status = "missing"
        items.append({"doc_type": d, "label": meta["label"], "status": status, "required_by": sorted(used_by),
                      "auto_source": meta["auto"],
                      "document_id": up[d].id if d in up else None})
    order = {"missing": 0, "fetchable": 1, "after_sanction": 2, "auto": 3, "fetched": 4, "uploaded": 5}
    items.sort(key=lambda i: order[i["status"]])
    ready = sum(i["status"] in ("uploaded", "fetched", "auto", "after_sanction") for i in items)
    manual = sum(i["status"] == "missing" for i in items)
    return {"schemes": schemes, "items": items,
            "stats": {"traditional": TRADITIONAL_DOC_COUNT, "required": len(items), "ready": ready,
                      "auto_fetchable": sum(i["status"] == "fetchable" for i in items), "owner_must_upload": manual,
                      "completeness": round(ready / len(items), 3) if items else 0}}
