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

log = logging.getLogger(__name__)


def _tg_post(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "8481347460:AAGh94HRDgOwvSEJJt0B58WFl-vxtlGYO5I")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        log.warning("Telegram not configured — skipping alert. Set TELEGRAM_CHAT_ID in .env")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":                  chat_id,
                "text":                     text,
                "parse_mode":               parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        time.sleep(0.5)  # Telegram rate limit buffer
        return resp.status_code == 200
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
        "⚡ <b>NEW JOB DETECTED</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{company}</b>\n"
        f"💼 {title}\n"
        f"📍 {location}\n"
        f"🛂 {h1b}\n"
        f"📅 Posted: {posted}\n"
        f"🔗 <a href='{url}'>Apply Now</a>\n\n"
        "🤖 <i>AI scoring in progress...</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _tg_post(msg)
    log.info(f"📱 Wave 1 sent — {title} @ {company}")


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

    strengths_text = "\n".join(f"  ✅ {s}" for s in strengths[:3]) or "  ✅ Strong ML/AI match"
    gaps_text      = "\n".join(f"  ⚠️ {g}" for g in gaps[:2])     or "  ✅ No major gaps"

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>{score}/100 — {verdict} {emoji}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{company}</b> | {title}\n"
        f"📍 {location} | 💰 {salary}\n"
        f"🏅 H1B: {h1b}\n"
        f"{time_badge}\n\n"
        f"<b>✅ YOUR EDGE:</b>\n{strengths_text}\n\n"
        f"<b>⚠️ WATCH OUT:</b>\n{gaps_text}\n\n"
        f"<b>💡 INSIDER TIP:</b>\n{tip[:300]}\n\n"
        f"📄 /cl_{job_id}       → Cover letter\n"
        f"✅ /applied_{job_id}  → Mark applied\n"
        f"🚫 /skip_{job_id}     → Not interested\n"
        f"🔗 <a href='{url}'>Apply Now ↗</a>\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _tg_post(msg)
    log.info(f"📱 Wave 2 sent — {score}/100 | {title} @ {company}")


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
