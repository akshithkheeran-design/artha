"""Scheme knowledge base. Every rule carries the source it was taken from.

Figures are summarised from the official portals / guidelines listed in each citation. They are indicative;
the lender or scheme agency makes the final decision and guidelines change, so every citation carries the
date it was last checked and the UI asks users to confirm on the official portal.
"""
VERIFIED_ON = "2026-11-01"


def cite(title: str, url: str, section: str) -> dict:
    return {"title": title, "url": url, "section": section, "verified_on": VERIFIED_ON}


C = {
    "mudra": cite("PMMY – MUDRA Offerings", "https://www.mudra.org.in/Offerings",
                  "Shishu / Kishore / Tarun loan categories"),
    "mudra_faq": cite("PMMY – Frequently Asked Questions", "https://www.mudra.org.in/faq",
                      "Who can avail MUDRA loans; activities covered"),
    "mudra_tp": cite("Union Budget 2024-25 – Budget Speech", "https://www.indiabudget.gov.in/",
                     "MUDRA limit enhanced to ₹20 lakh (Tarun Plus) for borrowers who repaid Tarun loans"),
    "pmegp": cite("PMEGP – Scheme Guidelines (KVIC)", "https://www.kviconline.gov.in/pmegp/pmegpweb/index.jsp",
                  "Eligibility conditions of beneficiaries"),
    "pmegp_fin": cite("PMEGP – Scheme Guidelines (KVIC)", "https://www.kviconline.gov.in/pmegp/pmegpweb/index.jsp",
                      "Quantum and nature of financial assistance (margin money subsidy)"),
    "sui": cite("Stand-Up India – Scheme details", "https://www.standupmitra.in/Home/SUISchemes",
                "Eligibility"),
    "cgtmse": cite("CGTMSE – Credit Guarantee Scheme", "https://www.cgtmse.in/",
                   "Eligible lending institutions, borrowers and credit facilities"),
    "cgtmse_b25": cite("Union Budget 2025-26 – Budget Speech", "https://www.indiabudget.gov.in/",
                       "Credit guarantee cover for micro & small enterprises enhanced from ₹5 crore to ₹10 crore"),
    "svanidhi": cite("PM SVANidhi – Scheme portal", "https://pmsvanidhi.mohua.gov.in/",
                     "Eligibility of street vendors; loan tranches"),
    "svanidhi_25": cite("PIB – Cabinet approves restructuring of PM SVANidhi (Aug 2025)", "https://pib.gov.in/",
                        "Tranche 1 ₹15,000, Tranche 2 ₹25,000, Tranche 3 ₹50,000; extended to March 2030"),
    "vishwakarma": cite("PM Vishwakarma – Scheme Guidelines", "https://pmvishwakarma.gov.in/",
                        "Eligibility criteria and 18 covered trades"),
    "vishwakarma_cr": cite("PM Vishwakarma – Scheme Guidelines", "https://pmvishwakarma.gov.in/",
                           "Credit support: ₹1 lakh + ₹2 lakh tranches at 5% concessional interest"),
    "nrlm": cite("RBI Master Circular – DAY-NRLM", "https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx",
                 "SHG eligibility, collateral-free lending and interest subvention"),
    "nrlm_portal": cite("DAY-NRLM (Aajeevika)", "https://aajeevika.gov.in/", "SHG–Bank linkage"),
    "kcc_ah": cite("RBI – Statement on Developmental and Regulatory Policies (6 Dec 2024)",
                   "https://www.rbi.org.in/", "Collateral-free agricultural loan limit raised from ₹1.6 lakh to ₹2 lakh"),
    "kcc_dahd": cite("DAHD – KCC for Animal Husbandry & Dairy farmers", "https://dahd.gov.in/",
                     "Working-capital KCC for animal husbandry and dairy"),
    "udyam": cite("Udyam Registration portal", "https://udyamregistration.gov.in/",
                  "Free online registration; MSME classification (revised w.e.f. 1 Apr 2025)"),
}

VISHWAKARMA_TRADES = [
    "carpenter", "boat maker", "armourer", "blacksmith", "hammer and tool kit maker", "locksmith", "goldsmith",
    "potter", "sculptor", "cobbler", "mason", "basket/mat/broom maker", "doll and toy maker", "barber",
    "garland maker", "washerman", "tailor", "fishing net maker",
]

SPECIAL_CATEGORIES = {"sc", "st", "obc", "minority"}

SCHEMES = [
    {
        "id": "mudra", "name": "Pradhan Mantri MUDRA Yojana (PMMY)", "agency": "Banks, NBFCs, MFIs, SFBs",
        "short": "MUDRA", "max_amount": 2_000_000, "typical_rate": "Lender-set (RBI-linked); no collateral",
        "benefit": "Collateral-free loans for non-farm income-generating micro enterprises — Shishu up to ₹50,000, "
                   "Kishore ₹50,001–₹5 lakh, Tarun ₹5–10 lakh, Tarun Plus ₹10–20 lakh.",
        "citations": [C["mudra"], C["mudra_faq"], C["mudra_tp"]],
        "documents": ["kyc_aadhaar", "pan", "business_proof", "bank_statement", "photo", "quotation"],
    },
    {
        "id": "pmegp", "name": "Prime Minister's Employment Generation Programme (PMEGP)",
        "agency": "KVIC / KVIB / District Industries Centre + bank", "short": "PMEGP", "max_amount": 5_000_000,
        "typical_rate": "Bank rate on loan; 15–35% of project cost as margin-money subsidy",
        "benefit": "Margin-money subsidy for NEW micro units: project up to ₹50 lakh (manufacturing) / ₹20 lakh "
                   "(service). Subsidy 15% urban / 25% rural (general); 25% / 35% for special categories.",
        "citations": [C["pmegp"], C["pmegp_fin"]],
        "documents": ["kyc_aadhaar", "pan", "project_report", "education_cert", "caste_cert", "rural_cert",
                      "photo", "edp_cert"],
    },
    {
        "id": "standup", "name": "Stand-Up India", "agency": "Scheduled commercial bank branches",
        "short": "Stand-Up India", "max_amount": 10_000_000, "typical_rate": "Lowest applicable bank rate",
        "benefit": "Composite loan of ₹10 lakh – ₹1 crore for a greenfield enterprise set up by an SC/ST and/or "
                   "woman entrepreneur.",
        "citations": [C["sui"]],
        "documents": ["kyc_aadhaar", "pan", "project_report", "caste_cert", "business_proof", "photo", "quotation"],
    },
    {
        "id": "cgtmse", "name": "Credit Guarantee Fund Trust for Micro & Small Enterprises (CGTMSE)",
        "agency": "Member lending institutions (banks / NBFCs)", "short": "CGTMSE", "max_amount": 100_000_000,
        "typical_rate": "Lender rate + annual guarantee fee",
        "benefit": "Lender gets a credit guarantee so it can lend to MSEs WITHOUT collateral or third-party "
                   "guarantee (cover up to ₹10 crore per borrower).",
        "citations": [C["cgtmse"], C["cgtmse_b25"], C["udyam"]],
        "documents": ["udyam", "kyc_aadhaar", "pan", "bank_statement"],
    },
    {
        "id": "vishwakarma", "name": "PM Vishwakarma", "agency": "Ministry of MSME via banks & CSCs",
        "short": "PM Vishwakarma", "max_amount": 300_000, "typical_rate": "5% concessional interest",
        "benefit": "For traditional artisans in 18 trades (e.g. tailor, blacksmith, carpenter): collateral-free "
                   "credit ₹1 lakh then ₹2 lakh at 5%, toolkit e-voucher, skilling with stipend.",
        "citations": [C["vishwakarma"], C["vishwakarma_cr"]],
        "documents": ["kyc_aadhaar", "bank_statement", "ration_card", "photo"],
    },
    {
        "id": "svanidhi", "name": "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "agency": "Banks, NBFCs, MFIs via Urban Local Bodies", "short": "PM SVANidhi", "max_amount": 50_000,
        "typical_rate": "7% interest subsidy + digital-payment cashback",
        "benefit": "Working-capital loans for urban street vendors: ₹15,000 → ₹25,000 → ₹50,000 on timely repayment.",
        "citations": [C["svanidhi"], C["svanidhi_25"]],
        "documents": ["kyc_aadhaar", "vending_cert", "bank_statement"],
    },
    {
        "id": "nrlm", "name": "DAY-NRLM SHG–Bank Linkage", "agency": "Banks via State Rural Livelihood Missions",
        "short": "SHG Bank Linkage", "max_amount": 2_000_000, "typical_rate": "Interest subvention for women SHGs",
        "benefit": "Collateral-free cash-credit / term loans to women Self-Help Groups (up to ₹20 lakh without "
                   "collateral) with interest subvention.",
        "citations": [C["nrlm"], C["nrlm_portal"]],
        "documents": ["shg_resolution", "shg_books", "kyc_aadhaar", "bank_statement"],
    },
    {
        "id": "kcc_ah", "name": "Kisan Credit Card – Animal Husbandry & Dairy", "agency": "Banks, RRBs, co-op banks",
        "short": "KCC (Dairy)", "max_amount": 300_000, "typical_rate": "Subvented short-term rate with prompt-repayment incentive",
        "benefit": "Working-capital credit for dairy / animal-husbandry units; collateral-free up to ₹2 lakh.",
        "citations": [C["kcc_dahd"], C["kcc_ah"]],
        "documents": ["kyc_aadhaar", "land_or_shed_proof", "livestock_details", "bank_statement", "photo"],
    },
]
SCHEME_INDEX = {s["id"]: s for s in SCHEMES}

DOCUMENTS = {
    "kyc_aadhaar": {"label": "Aadhaar e-KYC", "auto": "digilocker", "core": True},
    "pan": {"label": "PAN card", "auto": "digilocker", "core": True},
    "udyam": {"label": "Udyam Registration certificate", "auto": "digilocker", "core": True},
    "bank_statement": {"label": "Bank / UPI statement (12 months)", "auto": "aa", "core": True},
    "photo": {"label": "Passport photo", "auto": None, "core": True},
    "business_proof": {"label": "Business address / existence proof", "auto": None, "core": True},
    "quotation": {"label": "Quotation for machinery / stock", "auto": None, "core": False},
    "project_report": {"label": "Project report (auto-drafted by ARTHA)", "auto": "artha", "core": False},
    "education_cert": {"label": "Education certificate (8th pass)", "auto": "digilocker", "core": False},
    "caste_cert": {"label": "Caste / category certificate", "auto": "digilocker", "core": False},
    "rural_cert": {"label": "Rural area certificate", "auto": None, "core": False},
    "edp_cert": {"label": "EDP training certificate (after sanction)", "auto": None, "core": False},
    "ration_card": {"label": "Ration card (family identification)", "auto": "digilocker", "core": False},
    "vending_cert": {"label": "Certificate of Vending / ULB letter", "auto": None, "core": False},
    "shg_resolution": {"label": "SHG resolution to borrow", "auto": None, "core": False},
    "shg_books": {"label": "SHG books / grading sheet", "auto": None, "core": False},
    "land_or_shed_proof": {"label": "Cattle-shed / land proof", "auto": None, "core": False},
    "livestock_details": {"label": "Livestock details", "auto": None, "core": False},
}
