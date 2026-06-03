"""
companies.py — All ATS endpoints (verified working as of May 2026).

Active sources:
  - Greenhouse: 46 companies (direct JSON API)
  - Ashby: 25 companies (direct JSON API)
  - Workday: 23 companies (CXS POST API)
  - Amazon: 1 (requests-based, zstd workaround)
  - H1B GitHub Feed: daily markdown
  - JobSpy: Indeed + Google Jobs

Removed (dead APIs):
  - Lever (companies migrated off)
  - Google Careers API (deprecated)
  - Microsoft Careers (SSL broken)
  - Apple Jobs API (404)
  - HuggingFace/Workable (404)
"""

# ─────────────────────────────────────────────────────────────────
# GREENHOUSE — 46 companies (verified working, JSON API)
# ─────────────────────────────────────────────────────────────────

TIER1_GREENHOUSE = [
    # Big Tech
    "nvidia", "scaleai", "datadog", "palantir", "mongodb",
    # Fintech
    "stripe", "coinbase", "robinhood", "brex", "ramp", "plaid",
    "affirm", "marqeta", "chime",
    # Infrastructure
    "elastic", "confluent", "hashicorp", "cloudflare",
    "fastly", "snyk", "checkr",
    # SaaS / Product
    "notionhq", "asana", "intercom", "lattice", "gusto",
    "squarespace", "box", "hubspot", "zendesk",
    # Consumer / Marketplace
    "airbnb", "doordash", "lyft", "reddit", "twilio",
    # Data / Analytics
    "snowflake", "segment", "amplitude",
    # Design / Creative
    "figma", "canva", "loom",
    # AI / Biotech
    "anthropic", "flexport", "benchling", "dropbox", "persona",
]

# ─────────────────────────────────────────────────────────────────
# ASHBY — 25 companies (verified working, JSON API)
# ─────────────────────────────────────────────────────────────────

TIER1_ASHBY = [
    # AI-first companies
    "openai", "anthropic", "mistral",
    # Dev tools / Infra
    "linear", "perplexityai", "vercel", "supabase", "retool",
    "mercury", "watershed", "arc", "modal", "cohere",
    "anyscale", "runway", "cursor", "codeium",
    # Data / ML
    "openbb", "roboflow", "encord", "vellum",
    "dagster", "turso", "neon", "xata",
]

# ─────────────────────────────────────────────────────────────────
# WORKDAY — 23 companies (CXS POST API, verified working)
# ─────────────────────────────────────────────────────────────────

TIER2_WORKDAY = {
    # Big Tech
    "nvidia":             "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
    "intel":              "https://intel.wd1.myworkdayjobs.com/wday/cxs/intel/External/jobs",
    "salesforce":         "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs",
    "ibm":                "https://ibm.wd3.myworkdayjobs.com/wday/cxs/ibm/IBMExternalSite/jobs",
    "oracle":             "https://oracle.wd1.myworkdayjobs.com/wday/cxs/oracle/OracleCareers/jobs",
    "amd":                "https://amd.wd1.myworkdayjobs.com/wday/cxs/amd/AMD/jobs",
    "qualcomm":           "https://qualcomm.wd5.myworkdayjobs.com/wday/cxs/qualcomm/External/jobs",
    "broadcom":           "https://broadcom.wd1.myworkdayjobs.com/wday/cxs/broadcom/External_Career_Site/jobs",
    "servicenow":         "https://servicenow.wd5.myworkdayjobs.com/wday/cxs/servicenow/External/jobs",
    "workday_inc":        "https://workday.wd5.myworkdayjobs.com/wday/cxs/workday/Workday/jobs",
    "palo_alto_networks": "https://paloaltonetworks.wd1.myworkdayjobs.com/wday/cxs/paloaltonetworks/External/jobs",
    "crowdstrike":        "https://crowdstrike.wd5.myworkdayjobs.com/wday/cxs/crowdstrike/crowdstrikecareers/jobs",
    "fortinet":           "https://fortinet.wd1.myworkdayjobs.com/wday/cxs/fortinet/External/jobs",
    # Universities — Cap-Exempt H1B (no lottery!)
    "carnegie_mellon":    "https://cmu.wd5.myworkdayjobs.com/wday/cxs/cmu/CMU/jobs",
    "umich":              "https://umich.wd1.myworkdayjobs.com/wday/cxs/umich/UMJobs/jobs",
    "penn_state":         "https://psu.wd1.myworkdayjobs.com/wday/cxs/psu/PSU_Staff/jobs",
    "purdue":             "https://careers.purdue.edu/wday/cxs/purdue/External/jobs",
    "ut_austin":          "https://utaustin.wd1.myworkdayjobs.com/wday/cxs/utaustin/UTstaff/jobs",
    "ohio_state":         "https://osu.wd1.myworkdayjobs.com/wday/cxs/osu/OSUCareers/jobs",
    "georgia_tech":       "https://gatech.wd1.myworkdayjobs.com/wday/cxs/gatech/GTech/jobs",
    "columbia":           "https://columbia.wd5.myworkdayjobs.com/wday/cxs/columbia/External/jobs",
    "mongodb":            "https://mongodb.wd5.myworkdayjobs.com/wday/cxs/mongodb/MongoDB_External/jobs",
    "elastic":            "https://elastic.wd1.myworkdayjobs.com/wday/cxs/elastic/ElasticCareers/jobs",
}

# ─────────────────────────────────────────────────────────────────
# H1B GITHUB DAILY FEED (free, pre-filtered for H1B)
# ─────────────────────────────────────────────────────────────────

H1B_FEED_BASE = (
    "https://raw.githubusercontent.com/jobright-ai/"
    "Daily-H1B-Jobs-In-Tech/master/Job-Listings/{year}/{date}.md"
)

# ─────────────────────────────────────────────────────────────────
# JOBSPY PORTALS (via python-jobspy — Indeed + Google working)
# ─────────────────────────────────────────────────────────────────

JOBSPY_PORTALS = ["indeed", "google"]
