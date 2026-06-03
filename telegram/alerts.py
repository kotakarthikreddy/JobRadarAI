"""
alerts.py — Wave 1 + Wave 2 Telegram alert formatters for JobRadar AI v5.0
Uses real bot token from env.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from telegram.config import get_chat_id

log = logging.getLogger(__name__)


def _tg_post(text: str, parse_mode: str = "") -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = get_chat_id()
    if not token or not chat_id:
        log.warning("Telegram not configured — set TELEGRAM_CHAT_ID in Settings or message @KotaKarthik_bot /start")
        return False
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Telegram API error: %s", resp.text[:200])
            return False
        time.sleep(0.5)
        return True
    except Exception as e:
        log.error(f"Telegram send error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
# WAVE 1 — Fires immediately on detection (~10 sec)
# ─────────────────────────────────────────────────────────────────

def send_wave1(job: dict) -> None:
    """Instant alert — no AI score yet."""
    company  = job.get("company", "Unknown")
    title    = job.get("title", "Unknown Role")
    location = job.get("location", "Unknown")
    url      = job.get("url", "")
    posted   = job.get("posted", "Recently")
    h1b      = job.get("h1b_status", "❓ Unknown")

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ NEW JOB DETECTED\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 {company}\n"
        f"💼 {title}\n"
        f"📍 {location}\n"
        f"🏅 {h1b}\n"
        f"⏱️ Posted: {posted}\n"
        f"🔗 {url}\n\n"
        "🤖 AI scoring in progress..."
    )
    _tg_post(msg)
    log.info("Wave 1 sent — %s @ %s", title, company)


# ─────────────────────────────────────────────────────────────────
# WAVE 2 — Fires after AI scoring (~60 sec)
# ─────────────────────────────────────────────────────────────────

def send_wave2(job: dict, score_result: dict) -> None:
    """Full analysis alert with score, strengths, gaps, cover letter link."""
    company   = job.get("company", "Unknown")
    title     = job.get("title", "Unknown Role")
    location  = job.get("location", "Unknown")
    url       = job.get("url", "")
    job_id    = str(job.get("job_id", ""))[:12]

    score     = score_result.get("match_score", 0)
    verdict   = score_result.get("verdict", "APPLY")
    emoji     = score_result.get("verdict_emoji", "✅")
    strengths = score_result.get("top_strengths", [])
    gaps      = score_result.get("skill_gaps", [])
    salary    = score_result.get("salary_estimate", "N/A")
    tip       = score_result.get("insider_tip", "")
    time_badge = score_result.get("time_badge", "")
    h1b       = "✅ Verified" if job.get("h1b_verified") else "❓ Unknown"
    h1b_detail = job.get("h1b_status", h1b)

    strengths_text = "\n".join(f"  • {s}" for s in strengths[:3]) if strengths else "  • ML/AI domain match"
    gaps_text = "\n".join(f"  • {g}" for g in gaps[:2]) if gaps else "  • None critical"

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 {score}/100 — {verdict} {emoji}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 {company} | {title}\n"
        f"📍 {location} | 💰 {salary}\n"
        f"🏅 H1B: {h1b_detail}\n"
        f"{time_badge}\n\n"
        f"✅ YOUR EDGE:\n{strengths_text}\n\n"
        f"⚠️ WATCH OUT:\n{gaps_text}\n\n"
        f"💡 TIP: {tip}\n\n"
        f"🔗 {url}\n\n"
        f"/cl_{job_id} → Cover letter\n"
        f"/applied_{job_id} → Mark applied\n"
        f"/skip_{job_id} → Not interested\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _tg_post(msg)
    log.info("Wave 2 sent — %s/100 | %s @ %s", score, title, company)


# ─────────────────────────────────────────────────────────────────
# CRASH ALERT
# ─────────────────────────────────────────────────────────────────

def send_crash_alert(error: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _tg_post(
        f"🔴 <b>JOBRADAR CRASHED</b>\n\n"
        f"⏰ {now}\n"
        f"❌ {error[:400]}\n\n"
        "Restart the scanner."
    )


# ─────────────────────────────────────────────────────────────────
# STATUS ALERT
# ─────────────────────────────────────────────────────────────────

def send_status(stats: dict, uptime: str) -> None:
    _tg_post(
        f"📊 <b>JobRadar Live</b>\n"
        f"✅ Uptime: {uptime}\n"
        f"🔍 Seen today: {stats.get('seen_today', 0)}\n"
        f"🎯 Alerts sent: {stats.get('total_alerted', 0)}\n"
        f"📬 Applied: {stats.get('applied', 0)}\n"
        f"💼 Interviewing: {stats.get('interviewing', 0)}"
    )


def send_scan_summary(scan_result: dict) -> None:
    """Send a brief summary after every scan so user knows it's alive."""
    total    = scan_result.get("total", 0)
    filtered = scan_result.get("filtered", 0)
    duped    = scan_result.get("duped", 0)
    alerted  = scan_result.get("alerted", 0)
    elapsed  = scan_result.get("elapsed_s", 0)

    if alerted > 0:
        # Batch alert already sent — no need for extra noise
        return

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📡 SCAN COMPLETE\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 Fetched: {total} jobs\n"
        f"⛔ Filtered: {filtered}\n"
        f"🔁 Already seen: {duped}\n"
        f"🆕 New alerts: {alerted}\n"
        f"⏱️ Time: {elapsed}s\n\n"
        "No new ML/AI jobs this cycle.\n"
        "Next scan in 30 min."
    )
    _tg_post(msg)


# ─────────────────────────────────────────────────────────────────
# BATCH ALERT — All new jobs in one message
# ─────────────────────────────────────────────────────────────────

def send_batch_alert(jobs_with_scores: list) -> None:
    """Send all new jobs as one consolidated Telegram message."""
    if not jobs_with_scores:
        return

    count = len(jobs_with_scores)
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")

    # Header
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 {count} NEW ML/AI JOBS FOUND",
        f"⏰ {now}",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]

    # Each job as a compact entry
    for i, (job, score_result) in enumerate(jobs_with_scores, 1):
        company = job.get("company", "?")
        title = job.get("title", "?")
        location = job.get("location", "?")
        url = job.get("url", "")
        score = score_result.get("match_score", 0)
        verdict = score_result.get("verdict", "")
        emoji = score_result.get("verdict_emoji", "")
        h1b = "✅" if job.get("h1b_verified") else "❓"
        salary = score_result.get("salary_estimate", "")
        job_id = str(job.get("job_id", ""))[:12]

        lines.append(
            f"{i}. {score}/100 {emoji} {verdict}\n"
            f"   🏢 {company} — {title}\n"
            f"   📍 {location} | H1B: {h1b}"
            + (f" | 💰 {salary}" if salary and salary != "Unknown" else "")
            + f"\n   🔗 {url}\n"
            f"   /applied_{job_id} · /cl_{job_id}\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"Next scan in 30 min.")

    full_msg = "\n".join(lines)

    # Telegram has 4096 char limit — split if needed
    if len(full_msg) <= 4000:
        _tg_post(full_msg)
    else:
        # Send in chunks
        chunk_size = 5
        for start in range(0, count, chunk_size):
            chunk = jobs_with_scores[start:start + chunk_size]
            chunk_lines = [
                "━━━━━━━━━━━━━━━━━━━━━━",
                f"🎯 Jobs {start+1}–{start+len(chunk)} of {count}",
                "━━━━━━━━━━━━━━━━━━━━━━\n",
            ]
            for i, (job, score_result) in enumerate(chunk, start + 1):
                company = job.get("company", "?")
                title = job.get("title", "?")
                location = job.get("location", "?")
                url = job.get("url", "")
                score = score_result.get("match_score", 0)
                verdict = score_result.get("verdict", "")
                emoji = score_result.get("verdict_emoji", "")
                h1b = "✅" if job.get("h1b_verified") else "❓"
                job_id = str(job.get("job_id", ""))[:12]

                chunk_lines.append(
                    f"{i}. {score}/100 {emoji} {verdict}\n"
                    f"   🏢 {company} — {title}\n"
                    f"   📍 {location} | H1B: {h1b}\n"
                    f"   🔗 {url}\n"
                    f"   /applied_{job_id}\n"
                )
            _tg_post("\n".join(chunk_lines))
            time.sleep(1)

    log.info("Batch alert sent — %s jobs in one message", count)
