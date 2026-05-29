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
        "NEW ML JOB\n"
        f"{company}\n"
        f"{title}\n"
        f"{location} | {h1b}\n"
        f"Posted: {posted}\n"
        f"{url}\n"
        "Scoring..."
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
    job_id    = str(job.get("job_id", ""))[:8]

    score     = score_result.get("match_score", 0)
    verdict   = score_result.get("verdict", "APPLY")
    emoji     = score_result.get("verdict_emoji", "✅")
    strengths = score_result.get("top_strengths", [])
    gaps      = score_result.get("skill_gaps", [])
    salary    = score_result.get("salary_estimate", "N/A")
    tip       = score_result.get("insider_tip", "")
    time_badge = score_result.get("time_badge", "")
    h1b       = "✅ Verified" if job.get("h1b_verified") else "❓ Unknown"

    msg = (
        f"ML JOB — {score}/100 {verdict}\n"
        f"{company} | {title}\n"
        f"{location} | H1B: {h1b}\n"
        f"Apply: {url}\n"
        f"/applied_{job_id} or /skip_{job_id}"
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
