"""
orchestrator.py — Main async scan loop for JobRadar AI v5.0

Active sources (verified working):
  1. Greenhouse (46 companies) — 4,000+ jobs
  2. Ashby (25 companies) — 1,000+ jobs
  3. Workday (23 companies) — 150+ jobs
  4. Amazon Jobs (via requests) — 50+ jobs
  5. H1B GitHub Daily Feed — varies by day
  6. JobSpy (Indeed + Google) — 20+ jobs

Removed (APIs dead/changed as of May 2026):
  - Google Careers API (404)
  - Microsoft Careers (SSL broken)
  - Apple Jobs API (404)
  - HuggingFace/Workable (404)
  - Lever (most companies migrated off)
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
    TIER1_GREENHOUSE, TIER1_ASHBY, TIER2_WORKDAY,
    H1B_FEED_BASE, JOBSPY_PORTALS,
)
from scanner.filters import (
    apply_all_filters, detect_h1b, extract_resume_skills,
)
from db.storage import init_db, is_new_job, mark_job_seen, upsert_job, prune_old_jobs, get_db_stats, make_url_hash, make_title_hash
from ai.scorer import score_job, usage_report
from telegram.alerts import send_crash_alert, send_scan_summary, send_batch_alert

log = logging.getLogger(__name__)

_HTTP_SEM = asyncio.Semaphore(15)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/126 Safari/537.36"
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
                timeout=aiohttp.ClientTimeout(total=15),
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
                timeout=aiohttp.ClientTimeout(total=15),
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
    now = datetime.now(timezone.utc)
    dates = [
        now.strftime("%Y-%m-%d"),
        datetime.fromtimestamp(now.timestamp() - 86400, tz=timezone.utc).strftime("%Y-%m-%d"),
        datetime.fromtimestamp(now.timestamp() - 172800, tz=timezone.utc).strftime("%Y-%m-%d"),
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
        if jobs:
            log.info(f"  [H1B-Feed] {len(jobs)} jobs from {d}")
            return jobs
    log.info("  [H1B-Feed] 0 jobs (no feed available today)")
    return []


# ─────────────────────────────────────────────────────────────────
# SOURCE 2: GREENHOUSE (primary — 4,000+ jobs)
# ─────────────────────────────────────────────────────────────────

async def _fetch_greenhouse_one(session, company: str) -> list:
    data = await _get_json(session, f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true")
    if not data:
        return []
    jobs = []
    for p in data.get("jobs", []):
        jobs.append({
            "title":       p.get("title", ""),
            "company":     company.replace("-", " ").title(),
            "location":    p.get("location", {}).get("name", ""),
            "description": strip_html(p.get("content", "")),
            "url":         p.get("absolute_url", ""),
            "posted":      (p.get("updated_at") or "")[:10],
            "source":      f"Greenhouse/{company}",
            "job_id":      str(p.get("id", "")),
            "ats_type":    "greenhouse",
        })
    return jobs


async def fetch_greenhouse_jobs(session) -> list:
    log.info(f"🌿 [Greenhouse] Scanning {len(TIER1_GREENHOUSE)} companies…")
    tasks = [_fetch_greenhouse_one(session, c) for c in TIER1_GREENHOUSE]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Greenhouse] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 3: ASHBY (1,000+ jobs)
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
    tasks = [_fetch_ashby_one(session, c) for c in TIER1_ASHBY]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Ashby] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 4: AMAZON JOBS (via requests in executor — aiohttp can't handle zstd)
# ─────────────────────────────────────────────────────────────────

def _amazon_sync() -> list:
    try:
        import requests
        r = requests.get(
            "https://www.amazon.jobs/en/search.json",
            params={
                "base_query": "ML engineer OR AI engineer",
                "result_limit": "25",
                "normalized_country_code[]": "USA",
            },
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for hit in data.get("jobs", []):
            path = hit.get("job_path", "")
            jobs.append({
                "title":       hit.get("title", ""),
                "company":     "Amazon",
                "location":    hit.get("location", "USA"),
                "description": strip_html(hit.get("description_short") or hit.get("description", "")),
                "url":         f"https://amazon.jobs{path}" if path else "https://amazon.jobs",
                "posted":      (hit.get("posted_date") or "")[:10],
                "source":      "Amazon Jobs",
                "job_id":      str(hit.get("id_icims", "")),
                "ats_type":    "amazon",
            })
        return jobs
    except Exception as e:
        log.error(f"[Amazon] {e}")
        return []


async def fetch_amazon_jobs() -> list:
    log.info("📦 [Amazon] Scanning…")
    loop = asyncio.get_event_loop()
    jobs = await loop.run_in_executor(None, _amazon_sync)
    log.info(f"  [Amazon] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 5: WORKDAY (23 companies)
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
        ext = p.get("externalPath", "")
        apply = f"{base}{ext}" if ext else base
        jobs.append({
            "title":       p.get("title", ""),
            "company":     company.replace("_", " ").title(),
            "location":    p.get("locationsText", "USA"),
            "description": "",
            "url":         apply,
            "posted":      "Unknown",
            "source":      f"Workday/{company}",
            "job_id":      ext.strip("/").split("/")[-1] if ext else "",
            "ats_type":    "workday",
        })
    return jobs


async def fetch_workday_jobs(session, keyword: str = "AI engineer") -> list:
    log.info(f"🏗️  [Workday] Scanning {len(TIER2_WORKDAY)} companies…")
    tasks = [_fetch_workday_one(session, name, url, keyword) for name, url in TIER2_WORKDAY.items()]
    chunks = await asyncio.gather(*tasks, return_exceptions=True)
    jobs = [j for chunk in chunks if isinstance(chunk, list) for j in chunk]
    log.info(f"  [Workday] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 6: REMOTIVE (remote ML/AI jobs)
# ─────────────────────────────────────────────────────────────────

async def fetch_remotive_jobs(session) -> list:
    log.info("🌐 [Remotive] Scanning…")
    data = await _get_json(
        session,
        "https://remotive.com/api/remote-jobs",
        params={"category": "software-dev", "search": "machine learning", "limit": "30"},
    )
    if not data:
        return []
    jobs = []
    for p in data.get("jobs", []):
        jobs.append({
            "title":       p.get("title", ""),
            "company":     p.get("company_name", ""),
            "location":    p.get("candidate_required_location", "Remote"),
            "description": strip_html(p.get("description", "")),
            "url":         p.get("url", ""),
            "posted":      (p.get("publication_date") or "")[:10],
            "source":      "Remotive",
            "job_id":      str(p.get("id", "")),
            "ats_type":    "remotive",
        })
    log.info(f"  [Remotive] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 7: REMOTE OK (remote tech jobs)
# ─────────────────────────────────────────────────────────────────

def _remoteok_sync() -> list:
    try:
        import requests as req
        r = req.get(
            "https://remoteok.com/api",
            params={"tag": "machine-learning"},
            headers={"User-Agent": USER_AGENT},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for p in data:
            if not isinstance(p, dict) or not p.get("position"):
                continue
            jobs.append({
                "title":       p.get("position", ""),
                "company":     p.get("company", ""),
                "location":    p.get("location", "Remote"),
                "description": strip_html(p.get("description", "")),
                "url":         p.get("url", f"https://remoteok.com/l/{p.get('id','')}"),
                "posted":      (p.get("date") or "")[:10],
                "source":      "RemoteOK",
                "job_id":      str(p.get("id", "")),
                "ats_type":    "remoteok",
            })
        return jobs
    except Exception as e:
        log.error(f"[RemoteOK] {e}")
        return []


async def fetch_remoteok_jobs() -> list:
    log.info("🏠 [RemoteOK] Scanning…")
    loop = asyncio.get_event_loop()
    jobs = await loop.run_in_executor(None, _remoteok_sync)
    log.info(f"  [RemoteOK] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 8: Y COMBINATOR (Hacker News Who's Hiring)
# ─────────────────────────────────────────────────────────────────

async def fetch_ycombinator_jobs(session) -> list:
    log.info("🟠 [YC/HN] Scanning…")
    data = await _get_json(session, "https://hacker-news.firebaseio.com/v0/jobstories.json")
    if not data or not isinstance(data, list):
        return []
    # Fetch first 20 job details
    jobs = []
    for story_id in data[:20]:
        item = await _get_json(session, f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if not item:
            continue
        title = item.get("title", "")
        text = item.get("text", "")
        jobs.append({
            "title":       title,
            "company":     title.split("(")[0].strip() if "(" in title else "YC Startup",
            "location":    "Remote" if "remote" in (title + text).lower() else "USA",
            "description": strip_html(text),
            "url":         item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
            "posted":      datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc).strftime("%Y-%m-%d") if item.get("time") else "",
            "source":      "YCombinator/HN",
            "job_id":      str(story_id),
            "ats_type":    "ycombinator",
        })
    log.info(f"  [YC/HN] {len(jobs)} jobs")
    return jobs


# ─────────────────────────────────────────────────────────────────
# SOURCE 9: JOBSPY (Indeed + Google Jobs)
# ─────────────────────────────────────────────────────────────────

def _jobspy_sync() -> list:
    try:
        from jobspy import scrape_jobs
        df = scrape_jobs(
            site_name=JOBSPY_PORTALS,
            search_term="AI Engineer OR ML Engineer",
            location="United States",
            hours_old=168,
            results_wanted=25,
        )
        if df is None or df.empty:
            return []
        jobs = []
        for _, row in df.iterrows():
            url = str(row.get("job_url") or "").strip()
            if not url or url == "nan":
                continue
            desc = str(row.get("description") or "")
            desc = "" if desc == "nan" else desc
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
                "source":      f"JobSpy/{row.get('site', 'portal')}",
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
    start = time.monotonic()
    conn = init_db()
    pruned = prune_old_jobs(conn, days=30)
    if pruned:
        log.info(f"🗑️  Pruned {pruned} old jobs from DB.")

    resume_skills = extract_resume_skills(RESUME_TEXT)
    keyword = "AI Engineer"
    h1b_only = os.getenv("H1B_ONLY", "true").lower() in ("1", "true", "yes")

    log.info("=" * 60)
    log.info(f"🚀 SCAN #{_scan_stats['scans']+1} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    headers = {"User-Agent": USER_AGENT}
    connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        source_results = await asyncio.gather(
            fetch_h1b_feed(session),
            fetch_greenhouse_jobs(session),
            fetch_ashby_jobs(session),
            fetch_workday_jobs(session, keyword),
            fetch_amazon_jobs(),
            fetch_remotive_jobs(session),
            fetch_ycombinator_jobs(session),
            fetch_remoteok_jobs(),
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

    new_jobs_batch = []

    for job in all_jobs:
        if len(new_jobs_batch) >= max_alerts:
            log.info(f"   ⏸️  Reached MAX_ALERTS_PER_SCAN ({max_alerts}) — stopping.")
            break
        title = job.get("title", "?")
        company = job.get("company", "?")

        # H1B detection
        from_feed = "H1B-GitHub" in job.get("source", "")
        verified, label = detect_h1b(job, from_feed=from_feed)
        job["h1b_verified"] = job.get("h1b_verified") or verified
        job["h1b_status"] = job.get("h1b_status") or label

        # All hard filters
        passes, reason = apply_all_filters(job, resume_skills, h1b_only=h1b_only)
        if not passes:
            stats["filtered"] += 1
            continue

        # Google Sheets dedup (optional)
        try:
            from sheets.client import is_seen_in_sheets
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

        # Log to Seen IDs sheet
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

        # AI Scoring
        await asyncio.sleep(0.3)
        score_result = score_job(job, conn)
        if not score_result:
            continue

        score = score_result.get("match_score", 0)
        verdict = score_result.get("verdict", "")

        # Update DB
        mark_job_seen(conn, job, score=score)
        upsert_job(conn, job, score_result)
        stats["scored"] += 1

        # Score threshold
        if score < int(os.getenv("MIN_MATCH_SCORE", "60")) or verdict == "SKIP":
            log.info(f"   📉 Score {score} below threshold — skipped")
            continue

        # Collect for batch
        new_jobs_batch.append((job, score_result))
        stats["alerted"] += 1

        # Google Sheets
        try:
            from sheets.client import log_job_to_sheets
            log_job_to_sheets(job, score_result)
        except Exception as e:
            log.warning(f"   [Sheets] {e}")

    # ── Send ALL new jobs as ONE batch Telegram message ──────────
    if new_jobs_batch:
        from telegram.alerts import send_batch_alert
        send_batch_alert(new_jobs_batch)

    elapsed = round(time.monotonic() - start, 1)
    db_stats = get_db_stats(conn)

    try:
        from sheets.client import update_stats_dashboard
        update_stats_dashboard({**stats, "applied": db_stats.get("applied", 0)})
    except Exception:
        pass

    conn.close()

    _scan_stats["scans"] += 1
    _scan_stats["total_fetched"] += stats["total"]
    _scan_stats["alerted"] += stats["alerted"]
    _scan_stats["last_scan"] = datetime.now(timezone.utc).isoformat()

    log.info(f"✅ Scan done in {elapsed}s | Alerted: {stats['alerted']} | DB total: {db_stats.get('total_seen', 0)}")
    log.info(usage_report(init_db()))

    # Scan summary to Telegram
    from telegram.config import telegram_configured
    if telegram_configured():
        send_scan_summary({**stats, "elapsed_s": elapsed})

    return {**stats, "elapsed_s": elapsed, "db": db_stats}


def get_scanner_stats() -> dict:
    return _scan_stats
