"""
filters.py — All job filtering logic merged from OPT-Job-Scrapper + F1_H1B_Scraper + career-ops.
"""

import re
from datetime import datetime, timezone, timedelta

from config.candidate import (
    EXCLUDE_KEYWORDS, STAFFING_FIRMS, VERIFIED_H1B_SPONSORS, CORE_SKILLS, KEYWORD_FILTER
)


# ─────────────────────────────────────────────────────────────────
# H1B DETECTION
# ─────────────────────────────────────────────────────────────────

UNIVERSITY_KEYWORDS = [
    "university", "college", "institute of technology", "polytechnic",
    "carnegie mellon", "mit", "stanford", "harvard", "berkeley",
    "umich", "michigan", "penn state", "purdue", "ut austin", "uiuc",
    "ohio state", "georgia tech", "columbia", "caltech", "cornell",
    "yale", "princeton", "duke", "nyu", "usc", "ucsd",
]

H1B_POSITIVE_KEYWORDS = [
    "visa sponsorship", "h1b sponsor", "h1b visa", "sponsor h1b",
    "sponsorship available", "will sponsor", "sponsoring visa",
    "international candidates", "work authorization sponsorship",
    "immigration sponsorship", "visa support",
]


def _normalize_company(name: str) -> str:
    for s in (" inc", " llc", " corp", " ltd", " co", " group",
               " technologies", " solutions", ".", ",", "®", "™"):
        name = name.lower().replace(s, "")
    return name.strip()


def detect_h1b(job: dict, from_feed: bool = False) -> tuple[bool, str]:
    """Returns (verified: bool, label: str)."""
    company = str(job.get("company", ""))
    cl      = company.lower()
    cn      = _normalize_company(company)
    desc    = str(job.get("description", "")).lower()

    if from_feed:
        return True, "✅ Verified H1B (Daily Feed)"

    # University cap-exempt check
    for kw in UNIVERSITY_KEYWORDS:
        if kw in cl:
            return True, "🎓 Cap-Exempt University (No Lottery)"

    # Known sponsor list
    for sp in VERIFIED_H1B_SPONSORS:
        if sp in cn or cn in sp or sp in cl:
            return True, "✅ Known H1B Sponsor"

    # Explicit mention in JD
    for kw in H1B_POSITIVE_KEYWORDS:
        if kw in desc:
            return True, "✅ Sponsor (Mentioned in JD)"

    return False, "❓ H1B Status Unknown"


# ─────────────────────────────────────────────────────────────────
# KEYWORD FILTER (domain relevance)
# ─────────────────────────────────────────────────────────────────

def extract_resume_skills(resume: str) -> set:
    rl = resume.lower()
    return {s for s in CORE_SKILLS if s in rl}


def keyword_check(job: dict, resume_skills: set) -> tuple[int, bool]:
    """
    Returns (count, passes).
    Threshold = 1 if no description (title-only), else 2.
    """
    combined  = f"{job.get('title', '')} {job.get('description', '')}".lower()
    count     = sum(1 for s in resume_skills if s in combined)
    has_desc  = bool(job.get("description", "").strip())
    threshold = 2 if has_desc else 1
    return count, count >= threshold


def passes_ml_domain_filter(job: dict) -> bool:
    """Check if job is in the ML/AI/LLM domain."""
    combined = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(kw.lower() in combined for kw in KEYWORD_FILTER)


# ─────────────────────────────────────────────────────────────────
# EXCLUDE KEYWORD FILTER
# ─────────────────────────────────────────────────────────────────

def passes_exclude_filter(job: dict) -> tuple[bool, str]:
    """Returns (passes, reason_if_failed)."""
    combined = f"{job.get('title', '')} {job.get('description', '')}".lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in combined:
            return False, f"exclude keyword: '{kw}'"
    # Staffing firm check
    company = job.get("company", "").lower()
    for firm in STAFFING_FIRMS:
        if firm in company:
            return False, f"staffing firm: '{firm}'"
    return True, ""


# ─────────────────────────────────────────────────────────────────
# EXPERIENCE FILTER
# ─────────────────────────────────────────────────────────────────

def passes_experience_filter(job: dict, max_years: int = 8) -> tuple[bool, str]:
    """Reject if job explicitly requires more than max_years experience."""
    combined = f"{job.get('title', '')} {job.get('description', '')}".lower()
    patterns = [
        r'(\d+)\s*\+\s*years',
        r'(\d+)\s*years\s+of\s+(?:relevant\s+)?experience',
        r'minimum\s+(?:of\s+)?(\d+)\s*(?:\+\s*)?years',
        r'at\s+least\s+(\d+)\s*(?:\+\s*)?years',
        r'(\d+)\s*-\s*\d+\s*years',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, combined):
            years = int(m.group(1))
            if years > max_years:
                return False, f"requires {years}+ years (max {max_years})"
    return True, ""


# ─────────────────────────────────────────────────────────────────
# LOCATION FILTER (US-only)
# ─────────────────────────────────────────────────────────────────

US_INDICATORS = [
    "united states", "usa", "u.s.", "u.s.a", "remote", "hybrid",
    "new york", "san francisco", "los angeles", "chicago", "seattle",
    "austin", "boston", "denver", "atlanta", "dallas", "houston",
    "phoenix", "portland", "san diego", "san jose", "silicon valley",
    "washington", "miami", "detroit", "philadelphia", "minneapolis",
    "raleigh", "charlotte", "nashville", "salt lake", "pittsburgh",
    "mountain view", "palo alto", "sunnyvale", "cupertino", "menlo park",
    "redmond", "kirkland", "bellevue", "santa clara", "irvine",
    "allen", "plano", "frisco", "arlington", "richardson",
    "california", "texas", "new york", "virginia", "massachusetts",
    "illinois", "georgia", "north carolina", "colorado", "oregon",
    "pennsylvania", "florida", "maryland", "ohio", "michigan",
    ", al", ", ak", ", az", ", ar", ", ca", ", co", ", ct", ", de",
    ", fl", ", ga", ", hi", ", id", ", il", ", in", ", ia", ", ks",
    ", ky", ", la", ", me", ", md", ", ma", ", mi", ", mn", ", ms",
    ", mo", ", mt", ", ne", ", nv", ", nh", ", nj", ", nm", ", ny",
    ", nc", ", nd", ", oh", ", ok", ", or", ", pa", ", ri", ", sc",
    ", sd", ", tn", ", tx", ", ut", ", vt", ", va", ", wa", ", wv",
    ", wi", ", wy", ", dc",
]

NON_US_INDICATORS = [
    "canada", "uk", "united kingdom", "germany", "france", "india",
    "australia", "singapore", "japan", "china", "ireland", "netherlands",
    "brazil", "mexico", "israel", "sweden", "spain", "italy",
    "switzerland", "poland", "south korea", "london", "toronto",
    "vancouver", "berlin", "paris", "bangalore", "hyderabad",
    "mumbai", "dublin", "amsterdam", "sydney", "melbourne",
    "tokyo", "beijing", "shanghai", "tel aviv", "stockholm",
]


def passes_location_filter(job: dict) -> tuple[bool, str]:
    location = str(job.get("location", "")).lower()
    if not location or location in ("unknown", "n/a", "nan", ""):
        return True, ""
    for ind in US_INDICATORS:
        if ind in location:
            return True, ""
    for ind in NON_US_INDICATORS:
        if ind in location:
            return False, f"non-US location: '{job.get('location', '')}'"
    return True, ""   # can't determine → allow


# ─────────────────────────────────────────────────────────────────
# DATE FILTER
# ─────────────────────────────────────────────────────────────────

def passes_date_filter(job: dict, max_days_old: int = 7) -> tuple[bool, str]:
    """Allow jobs posted within max_days_old days."""
    posted = str(job.get("posted", "") or "").strip()
    if not posted or posted.lower() in ("unknown", "n/a", "nan", ""):
        return True, ""
    try:
        today = datetime.now(timezone.utc).date()
        cutoff = today - timedelta(days=max_days_old)
        posted_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                posted_date = datetime.strptime(posted[:10], fmt).date()
                break
            except ValueError:
                continue
        if posted_date is None:
            return True, ""
        if posted_date >= cutoff:
            return True, ""
        return False, f"posted {posted_date} (older than {max_days_old} days)"
    except Exception:
        return True, ""


# ─────────────────────────────────────────────────────────────────
# MASTER FILTER — runs all checks, returns (passes, reason)
# ─────────────────────────────────────────────────────────────────

def apply_all_filters(job: dict, resume_skills: set) -> tuple[bool, str]:
    """Apply all hard filters. Returns (passes, skip_reason)."""

    # ML/AI domain
    if not passes_ml_domain_filter(job):
        return False, "not ML/AI domain"

    # Exclude keywords + staffing
    ok, reason = passes_exclude_filter(job)
    if not ok:
        return False, reason

    # Experience
    ok, reason = passes_experience_filter(job)
    if not ok:
        return False, reason

    # Location
    ok, reason = passes_location_filter(job)
    if not ok:
        return False, reason

    # Date
    ok, reason = passes_date_filter(job)
    if not ok:
        return False, reason

    # Keyword relevance
    count, passes = keyword_check(job, resume_skills)
    if not passes:
        return False, f"low keyword match ({count})"

    return True, ""
