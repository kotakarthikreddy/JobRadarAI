"""
companies.py — All ATS endpoints organized by poll tier.
Tier 1: poll every 60 seconds (direct JSON APIs)
Tier 2: poll every 5 minutes (Workday / HTML)
"""

# ─────────────────────────────────────────────────────────────────
# TIER 1 — 60-second poll (direct JSON APIs from system prompt)
# ─────────────────────────────────────────────────────────────────

TIER1_LEVER = [
    "netflix", "cohere", "stripe", "uber", "airbnb", "twilio",
    "scaleai", "rippling", "airtable", "deel", "remote", "webflow",
    "postman", "grammarly", "attentive", "braze", "klaviyo",
    "iterable", "thoughtspot", "wealthsimple", "lob", "gem",
    "kandji", "dbt-labs", "prefect", "airbyte",
    "databricks",  # also on Lever
]

TIER1_GREENHOUSE = [
    # From system prompt
    "nvidia", "scale_ai", "datadog", "palantir", "mongodb",
    # From OPT-Job-Scrapper (40 companies)
    "stripe", "coinbase", "robinhood", "brex", "ramp", "plaid",
    "affirm", "marqeta", "chime",
    "elastic", "confluent", "hashicorp", "cloudflare",
    "fastly", "snyk", "checkr",
    "notionhq", "asana", "intercom", "lattice", "gusto",
    "squarespace", "box", "hubspot", "zendesk",
    "airbnb", "doordash", "lyft", "reddit", "twilio",
    "snowflake", "segment", "amplitude",
    "figma", "canva", "loom",
    "anthropic", "flexport", "benchling", "dropbox", "persona",
]

TIER1_ASHBY = [
    # From system prompt
    "openai", "anthropic", "mistral",
    # From OPT-Job-Scrapper (22 companies)
    "linear", "perplexityai", "vercel", "supabase", "retool",
    "mercury", "watershed", "arc", "modal", "cohere",
    "anyscale", "runway", "cursor", "codeium",
    "openbb", "roboflow", "encord", "vellum",
    "dagster", "turso", "neon", "xata",
]

# Direct API endpoints for major companies (Tier 1)
TIER1_DIRECT = {
    "google": {
        "url": "https://careers.google.com/api/v3/search/",
        "params": {"company": "Google", "q": "machine+learning+engineer"},
        "type": "google",
    },
    "amazon": {
        "url": "https://www.amazon.jobs/en/search.json",
        "params": {"base_query": "ML engineer", "result_limit": "10"},
        "type": "amazon",
    },
    "microsoft": {
        "url": "https://gcsservices.careers.microsoft.com/search/api/v1/search",
        "params": {"q": "ML engineer", "pgSz": "20", "o": "Recent"},
        "type": "microsoft",
    },
    "apple": {
        "url": "https://jobs.apple.com/api/role/search",
        "params": {"filters[postingpostLocation][0]": "postLocation-USA"},
        "type": "apple",
    },
    "huggingface": {
        "url": "https://apply.workable.com/api/v3/accounts/hugging-face/jobs",
        "params": {},
        "type": "workable",
    },
}

# ─────────────────────────────────────────────────────────────────
# TIER 2 — 5-minute poll (Workday CXS + slow endpoints)
# ─────────────────────────────────────────────────────────────────

TIER2_WORKDAY = {
    # Big Tech on Workday
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
    "mongodb":            "https://mongodb.wd5.myworkdayjobs.com/wday/cxs/mongodb/MongoDB_External/jobs",
    "elastic":            "https://elastic.wd1.myworkdayjobs.com/wday/cxs/elastic/ElasticCareers/jobs",
    # Universities — Cap-Exempt H1B (no lottery!)
    "carnegie_mellon":    "https://cmu.wd5.myworkdayjobs.com/wday/cxs/cmu/CMU/jobs",
    "umich":              "https://umich.wd1.myworkdayjobs.com/wday/cxs/umich/UMJobs/jobs",
    "penn_state":         "https://psu.wd1.myworkdayjobs.com/wday/cxs/psu/PSU_Staff/jobs",
    "purdue":             "https://careers.purdue.edu/wday/cxs/purdue/External/jobs",
    "ut_austin":          "https://utaustin.wd1.myworkdayjobs.com/wday/cxs/utaustin/UTstaff/jobs",
    "ohio_state":         "https://osu.wd1.myworkdayjobs.com/wday/cxs/osu/OSUCareers/jobs",
    "georgia_tech":       "https://gatech.wd1.myworkdayjobs.com/wday/cxs/gatech/GTech/jobs",
    "columbia":           "https://columbia.wd5.myworkdayjobs.com/wday/cxs/columbia/External/jobs",
}

# ─────────────────────────────────────────────────────────────────
# H1B GITHUB DAILY FEED (free, pre-filtered for H1B)
# ─────────────────────────────────────────────────────────────────

H1B_FEED_BASE = (
    "https://raw.githubusercontent.com/jobright-ai/"
    "Daily-H1B-Jobs-In-Tech/master/Job-Listings/{year}/{date}.md"
)

# ─────────────────────────────────────────────────────────────────
# JOBSPY PORTALS (via python-jobspy)
# ─────────────────────────────────────────────────────────────────

JOBSPY_PORTALS = ["indeed", "google", "zip_recruiter", "glassdoor"]
