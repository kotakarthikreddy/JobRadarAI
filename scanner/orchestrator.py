"""
orchestrator.py — Main async scan loop for JobRadar AI v5.0
Merges best of OPT-Job-Scrapper + career-ops into a single pipeline.

Pipeline per job:
  1. Fetch all sources in parallel
  2. Keyword filter (ML/AI domain)
  3. H1B detection
  4. All hard filters
  5. 3-layer dedup check
  6. Wave 1 Telegram (immediate)
  7. AI scoring (Gemini/Groq/OpenRouter)
  8. Write to DB + Google Sheets
  9. Wave 2 Telegram (with full analysis)
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from config.candidate import RESUME_TEXT
from config.companies import (
    TIER1_GREENHOUSE, TIER1_LEVER, TIER1_ASHBY, TIER2_WORKDAY,
    TIER1_DIRECT, H1B_FEED_BASE, JOBSPY_PORTALS,
)
from scanner.filters import (
    apply_all_filters, detect_h1b, extract_resume_skills,
)
from db.storage import init_db, is_new_job, mark_job_seen, upsert_job, prune_old_jobs, get_db_stats, make_url_hash, make_title_hash
from ai.scorer import score_job, usage_report
from telegram.alerts import send_wave1, send_wave2, send_crash_alert

log = logging.getLogger(__name__)

_HTTP_SEM = asyncio.Semaphore(10)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/124 Safari/537.36"
)


def strip_html(html: str) -> str:
    if not html:
        return ""
    try:
        return BeautifulSoup(html, "html.parser").get_text(" ").strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()


# ─────────────────────────────────────────────────────────────────
# HTTP HELPERS
# ─────────────────────────────────────────────────────────────────

async def _get_json(session, url, params=None, headers=None):
    async with _HTTP_SEM:
        try:
            async with session.get(
                url, params=params, headers=headers or {},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200:
                    return None
                return await r.json(content_type=None)
        except Exception:
            return None


async def _post_json(session, url, payload, headers=None):
    async with _HTTP_SEM:
        try:
            async with session.post(
                url, json=payload,
                headers=headers or {"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as r:
                if r.status != 200:
                    return None
                return await r.json(content_type=None)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────
# SOURCE 1: H1B GITHUB DAILY FEED
# ─────────────────────────────────────────────────────────────────

async def fetch_h1b_feed(session) -> list:
    log.info("📋 [H1B-Feed] Fetching GitHub daily feed…")
    now   = datetime.now(timezone.utc)
    dates = [
        now.strftime("%Y-%m-%d"),
        datetime.fromtimestamp(now.timestamp() - 86400, tz=timezone.utc).strftime("%Y-%m-%d"),
    ]
    pattern = re.compile(
        r'\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|'
        r'\s*\[.*?\]\((https?://[^\)]+)\)',
        re.IGNORECASE,
    )
    for d in dates:
        url = H1B_FEED_BASE.format(year=d[:4], date=d)
        async with _HTTP_SEM:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200:
                        continue
                    content = await r.text()
            except Exception:
                continue
        jobs = []
        for line in content.splitlines():
            if "---" in line or line.strip().lower().startswith("|title"):
                continue
            m = pattern.search(line)
            if m:
                title, company, location, apply_url = [g.strip() for g in m.groups()]
                if title and company and apply_url:
                    jobs.append({
                        "title": title, "company": company, "location": location,
                        "description": "", "url": apply_url, "posted": d,
                        "source": "H1B-GitHub-Feed", "h1b_verified": True,
                        "h1b_status": "✅ Verified H1B (Daily Feed)",
                    })
        log.info(f"  [H1B-Feed] {len(jobs)} jobs from {d}")
        return jobs
    return []


# ─────────────────────────────────────────────────────────────────
# SOURCE 2: GREENHOUSE
# ─────────────────────────────────────────────────────────────────

async def _fetch_greenhouse_one(session, company: str) -> list:
    data = await _get_json(session, f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true")
    if not data:
        return []
    jobs = []
    for p in data.get("jobs", []):
        jobs.append({
            "title":        p.get("title", ""),
            "company":      company.replace("-", " ").title(),
            "location":     p.get("location", {}).get("name", ""),
            "description":  strip_html(p.get("content", "")),
            "url":          p.get("absolute_url", ""),
            "posted":       (p.get("updated_at") or "")[:10],
            "source":       f"Greenhouse/{company}",
            "job_id":       str(p.get("id", "")),
            "ats_type":     "greenhouse",
        })
    return jobs


async def fetch_greenhouse_jobs(session) -> list:
    log.info(f"🌿 [Greenhouse] Scanning {len(TIER1_GREENHOUSE)} companies…")
    tasks  = [_fetch_greenhouse_one(session, c) for c in TIER1_GREENHOUSE]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs   = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Greenhouse] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 3: LEVER
# ─────────────────────────────────────────────────────────────────

async def _fetch_lever_one(session, company: str) -> list:
    postings = await _get_json(session, f"https://api.lever.co/v0/postings/{company}?mode=json")
    if not postings or not isinstance(postings, list):
        return []
    jobs = []
    for p in postings:
        ts     = p.get("createdAt", 0)
        posted = (datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "Unknown")
        desc   = f"{p.get('descriptionPlain','') or ''} {p.get('additionalPlain','') or ''}".strip()
        jobs.append({
            "title":    p.get("text", ""),
            "company":  company.replace("-", " ").title(),
            "location": p.get("categories", {}).get("location", ""),
            "description": desc,
            "url":      p.get("hostedUrl", ""),
            "posted":   posted,
            "source":   f"Lever/{company}",
            "job_id":   p.get("id", ""),
            "ats_type": "lever",
        })
    return jobs


async def fetch_lever_jobs(session) -> list:
    log.info(f"⚙️  [Lever] Scanning {len(TIER1_LEVER)} companies…")
    tasks  = [_fetch_lever_one(session, c) for c in TIER1_LEVER]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs   = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Lever] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 4: ASHBY
# ─────────────────────────────────────────────────────────────────

async def _fetch_ashby_one(session, company: str) -> list:
    data = await _get_json(session, f"https://api.ashbyhq.com/posting-api/job-board/{company}")
    postings = data.get("jobs", data.get("jobPostings", [])) if data else []
    if not postings:
        return []
    jobs = []
    for p in postings:
        loc = p.get("location", "")
        if isinstance(loc, dict):
            loc = loc.get("name", "")
        jobs.append({
            "title":       p.get("title", ""),
            "company":     company.replace("-", " ").title(),
            "location":    loc or ("Remote" if p.get("isRemote") else ""),
            "description": strip_html(p.get("descriptionPlain", "") or p.get("descriptionHtml", "")),
            "url":         p.get("jobUrl", p.get("applyUrl", "")),
            "posted":      (p.get("publishedAt") or "")[:10],
            "source":      f"Ashby/{company}",
            "job_id":      str(p.get("id", "")),
            "ats_type":    "ashby",
        })
    return jobs


async def fetch_ashby_jobs(session) -> list:
    log.info(f"🔷 [Ashby] Scanning {len(TIER1_ASHBY)} companies…")
    tasks  = [_fetch_ashby_one(session, c) for c in TIER1_ASHBY]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs   = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Ashby] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 5: GOOGLE CAREERS
# ─────────────────────────────────────────────────────────────────

async def fetch_google_jobs(session) -> list:
    log.info("🔍 [Google] Scanning…")
    data = await _get_json(session, "https://careers.google.com/api/v3/search/",
                           params={"q": "machine learning engineer", "num": "20"})
    if not data:
        return []
    jobs = []
    for item in data.get("jobs", []):
        locs = item.get("locations", [])
        jobs.append({
            "title":    item.get("job_title", ""),
            "company":  "Google",
            "location": locs[0].get("display", "USA") if locs else "USA",
            "description": strip_html(item.get("description", "")),
            "url":      item.get("apply_url", "https://careers.google.com"),
            "posted":   (item.get("publish_date") or "")[:10],
            "source":   "Google Careers",
            "job_id":   str(item.get("id", "")),
            "ats_type": "google",
        })
    log.info(f"  [Google] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 6: AMAZON JOBS
# ─────────────────────────────────────────────────────────────────

async def fetch_microsoft_jobs(session) -> list:
    log.info("🪟 [Microsoft] Scanning…")
    data = await _get_json(
        session,
        "https://gcsservices.careers.microsoft.com/search/api/v1/search",
        params={"q": "ML engineer", "pgSz": "20", "o": "Recent"},
    )
    if not data:
        return []
    jobs = []
    result = (data.get("operationResult") or {}).get("result") or {}
    for item in result.get("jobs", []):
        jobs.append({
            "title":       item.get("title", ""),
            "company":     "Microsoft",
            "location":    item.get("properties", {}).get("locations", ["USA"])[0]
                           if item.get("properties", {}).get("locations") else "USA",
            "description": strip_html(item.get("description", "")),
            "url":         item.get("jobUrl", "https://careers.microsoft.com"),
            "posted":      (item.get("postingDate") or "")[:10],
            "source":      "Microsoft Careers",
            "job_id":      str(item.get("jobId", "")),
            "ats_type":    "microsoft",
        })
    log.info(f"  [Microsoft] {len(jobs)} jobs")
    return jobs


async def fetch_apple_jobs(session) -> list:
    log.info("🍎 [Apple] Scanning…")
    data = await _get_json(
        session,
        "https://jobs.apple.com/api/role/search",
        params={"query": "machine learning", "sort": "newest", "page": "1"},
    )
    if not data:
        return []
    jobs = []
    for item in data.get("searchResults", data.get("res", {}).get("searchResults", [])):
        jobs.append({
            "title":       item.get("postingTitle", item.get("title", "")),
            "company":     "Apple",
            "location":    item.get("locations", [{}])[0].get("name", "USA")
                           if item.get("locations") else "USA",
            "description": "",
            "url":         f"https://jobs.apple.com/en-us/details/{item.get('positionId', '')}",
            "posted":      (item.get("postDateInGMT") or "")[:10],
            "source":      "Apple Careers",
            "job_id":      str(item.get("positionId", "")),
            "ats_type":    "apple",
        })
    log.info(f"  [Apple] {len(jobs)} jobs")
    return jobs


async def fetch_huggingface_jobs(session) -> list:
    log.info("🤗 [HuggingFace] Scanning…")
    data = await _get_json(
        session,
        "https://apply.workable.com/api/v3/accounts/hugging-face/jobs",
    )
    if not data:
        return []
    jobs = []
    for p in data.get("results", data.get("jobs", [])):
        jobs.append({
            "title":       p.get("title", ""),
            "company":     "Hugging Face",
            "location":    p.get("location", {}).get("country", "Remote")
                           if isinstance(p.get("location"), dict) else str(p.get("location", "")),
            "description": strip_html(p.get("description", "")),
            "url":         p.get("url", p.get("application_url", "")),
            "posted":      (p.get("published", "") or "")[:10],
            "source":      "Workable/HuggingFace",
            "job_id":      str(p.get("shortcode", p.get("id", ""))),
            "ats_type":    "workable",
        })
    log.info(f"  [HuggingFace] {len(jobs)} jobs")
    return jobs


async def fetch_amazon_jobs(session) -> list:
    log.info("📦 [Amazon] Scanning…")
    data = await _get_json(session, "https://amazon.jobs/en/search.json",
                           params={"base_query": "ML engineer", "job_count": "20",
                                   "facets[]": "normalized_country_code",
                                   "normalized_country_code[0]": "USA"})
    if not data:
        return []
    jobs = []
    for hit in data.get("hits", []):
        path = hit.get("job_path", "")
        jobs.append({
            "title":    hit.get("title", ""),
            "company":  "Amazon",
            "location": hit.get("location", "USA"),
            "description": strip_html(hit.get("description_short") or hit.get("description", "")),
            "url":      f"https://amazon.jobs{path}" if path else "https://amazon.jobs",
            "posted":   (hit.get("posted_date") or "")[:10],
            "source":   "Amazon Jobs",
            "job_id":   str(hit.get("id_icims", "")),
            "ats_type": "amazon",
        })
    log.info(f"  [Amazon] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 7: WORKDAY
# ─────────────────────────────────────────────────────────────────

async def _fetch_workday_one(session, company: str, api_url: str, keyword: str) -> list:
    base = "/".join(api_url.split("/")[:3])
    data = await _post_json(session, api_url,
                            payload={"searchText": keyword, "limit": 20, "offset": 0},
                            headers={"Content-Type": "application/json", "Accept": "application/json",
                                     "User-Agent": USER_AGENT})
    if not data:
        return []
    jobs = []
    for p in data.get("jobPostings", []):
        ext   = p.get("externalPath", "")
        apply = f"{base}{ext}" if ext else base
        jobs.append({
            "title":    p.get("title", ""),
            "company":  company.replace("_", " ").title(),
            "location": p.get("locationsText", "USA"),
            "description": "",
            "url":      apply,
            "posted":   "Unknown",
            "source":   f"Workday/{company}",
            "job_id":   ext.strip("/").split("/")[-1] if ext else "",
            "ats_type": "workday",
        })
    return jobs


async def fetch_workday_jobs(session, keyword: str = "AI engineer") -> list:
    log.info(f"🏗️  [Workday] Scanning {len(TIER2_WORKDAY)} companies…")
    tasks  = [_fetch_workday_one(session, name, url, keyword) for name, url in TIER2_WORKDAY.items()]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs   = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Workday] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 8: JOBSPY PORTALS (sync → executor)
# ─────────────────────────────────────────────────────────────────

def _jobspy_sync() -> list:
    try:
        from jobspy import scrape_jobs
        df = scrape_jobs(
            site_name=JOBSPY_PORTALS,
            search_term="AI Engineer OR ML Engineer",
            location="United States",
            hours_old=48,
            results_wanted=20,
        )
        if df is None or df.empty:
            return []
        jobs = []
        for _, row in df.iterrows():
            url = str(row.get("job_url") or "").strip()
            if not url or url == "nan":
                continue
            desc   = str(row.get("description") or "")
            desc   = "" if desc == "nan" else desc
            posted = row.get("date_posted", "")
            if hasattr(posted, "strftime"):
                posted = posted.strftime("%Y-%m-%d")
            jobs.append({
                "title":       str(row.get("title") or "").strip(),
                "company":     str(row.get("company") or "").strip(),
                "location":    str(row.get("location") or "").strip(),
                "description": desc,
                "url":         url,
                "posted":      str(posted) if posted else "Unknown",
                "source":      f"JobSpy/{row.get('site','portal')}",
            })
        return jobs
    except ImportError:
        log.warning("[JobSpy] Not installed — pip install python-jobspy")
    except Exception as e:
        log.error(f"[JobSpy] {e}")
    return []


async def fetch_jobspy_jobs() -> list:
    log.info("📡 [JobSpy] Scanning portals…")
    loop = asyncio.get_event_loop()
    jobs = await loop.run_in_executor(None, _jobspy_sync)
    log.info(f"  [JobSpy] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# MAIN SCAN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────

_scan_stats = {
    "scans": 0, "total_fetched": 0, "alerted": 0,
    "last_scan": None, "start_time": datetime.now(timezone.utc),
}


async def run_scan() -> dict:
    global _scan_stats
    start   = time.monotonic()
    conn    = init_db()
    pruned  = prune_old_jobs(conn, days=30)
    if pruned:
        log.info(f"🗑️  Pruned {pruned} old jobs from DB.")

    resume_skills = extract_resume_skills(RESUME_TEXT)
    keyword       = "AI Engineer"
    h1b_only      = os.getenv("H1B_ONLY", "true").lower() in ("1", "true", "yes")

    log.info("=" * 60)
    log.info(f"🚀 SCAN #{_scan_stats['scans']+1} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    headers   = {"User-Agent": USER_AGENT}
    connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        source_results = await asyncio.gather(
            fetch_h1b_feed(session),
            fetch_greenhouse_jobs(session),
            fetch_lever_jobs(session),
            fetch_ashby_jobs(session),
            fetch_google_jobs(session),
            fetch_amazon_jobs(session),
            fetch_microsoft_jobs(session),
            fetch_apple_jobs(session),
            fetch_huggingface_jobs(session),
            fetch_workday_jobs(session, keyword),
            fetch_jobspy_jobs(),
            return_exceptions=True,
        )

    all_jobs = []
    for result in source_results:
        if isinstance(result, list):
            all_jobs.extend(result)

    log.info(f"📊 Total raw: {len(all_jobs)}")

    stats = {"total": len(all_jobs), "filtered": 0, "duped": 0, "scored": 0, "alerted": 0}
    max_alerts = int(os.getenv("MAX_ALERTS_PER_SCAN", "15"))

    for job in all_jobs:
        if stats["alerted"] >= max_alerts:
            log.info(f"   ⏸️  Reached MAX_ALERTS_PER_SCAN ({max_alerts}) — stopping this cycle.")
            break
        title   = job.get("title", "?")
        company = job.get("company", "?")

        # H1B detection
        from_feed = "H1B-GitHub" in job.get("source", "")
        verified, label = detect_h1b(job, from_feed=from_feed)
        job["h1b_verified"] = job.get("h1b_verified") or verified
        job["h1b_status"]   = job.get("h1b_status") or label

        # All hard filters
        passes, reason = apply_all_filters(job, resume_skills, h1b_only=h1b_only)
        if not passes:
            log.debug(f"   ⛔ {title} @ {company} — {reason}")
            stats["filtered"] += 1
            continue

        # Google Sheets dedup (optional layer 1+2)
        try:
            from sheets.client import is_seen_in_sheets, log_seen_id
            jid = str(job.get("job_id", ""))
            uhash = make_url_hash(str(job.get("url", "")))
            if is_seen_in_sheets(jid, uhash):
                stats["duped"] += 1
                continue
        except Exception:
            pass

        # 3-layer dedup (SQLite)
        if not is_new_job(conn, job):
            stats["duped"] += 1
            continue
        mark_job_seen(conn, job, score=0)
        try:
            from sheets.client import log_seen_id
            log_seen_id(
                str(job.get("job_id", "")),
                make_url_hash(str(job.get("url", ""))),
                make_title_hash(str(job.get("title", "")), str(job.get("company", ""))),
            )
        except Exception:
            pass

        log.info(f"   ✅ NEW: {title} @ {company} | {job.get('h1b_status')}")

        # Wave 1 Telegram (immediate)
        send_wave1(job)

        # AI Scoring (local rules if Gemini quota exceeded)
        await asyncio.sleep(0.5)
        score_result = score_job(job, conn)
        if not score_result:
            continue

        score   = score_result.get("match_score", 0)
        verdict = score_result.get("verdict", "")

        # Update DB with score
        mark_job_seen(conn, job, score=score)
        upsert_job(conn, job, score_result)

        stats["scored"] += 1

        # Apply score threshold
        if score < int(os.getenv("MIN_MATCH_SCORE", "60")) or verdict == "SKIP":
            log.info(f"   📉 Score {score} below threshold — no Wave 2")
            continue

        # Wave 2 Telegram (full analysis)
        send_wave2(job, score_result)
        stats["alerted"] += 1

        # Google Sheets (optional)
        try:
            from sheets.client import log_job_to_sheets
            log_job_to_sheets(job, score_result)
        except Exception as e:
            log.warning(f"   [Sheets] {e}")

    elapsed = round(time.monotonic() - start, 1)
    db_stats = get_db_stats(conn)

    try:
        from sheets.client import update_stats_dashboard
        update_stats_dashboard({**stats, "applied": db_stats.get("applied", 0)})
    except Exception:
        pass

    conn.close()

    _scan_stats["scans"]        += 1
    _scan_stats["total_fetched"] += stats["total"]
    _scan_stats["alerted"]       += stats["alerted"]
    _scan_stats["last_scan"]     = datetime.now(timezone.utc).isoformat()

    log.info(f"✅ Scan done in {elapsed}s | Alerted: {stats['alerted']} | DB total: {db_stats.get('total_seen', 0)}")
    log.info(usage_report(init_db()))
    return {**stats, "elapsed_s": elapsed, "db": db_stats}


def get_scanner_stats() -> dict:
    return _scan_stats
