"""
bot.py — Telegram bot command handlers for JobRadar AI v5.0
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone, timedelta

import requests

from db.storage import init_db, get_job_by_id, update_job_status, get_cover_letter, get_top_jobs, get_db_stats
from telegram.alerts import _tg_post, send_status

log = logging.getLogger(__name__)
BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
_offset    = 0
_start_time = datetime.now(timezone.utc)


def _get_uptime() -> str:
    delta = datetime.now(timezone.utc) - _start_time
    h, rem = divmod(int(delta.total_seconds()), 3600)
    return f"{h}h {rem // 60}m"


def _get_updates():
    global _offset
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"timeout": 20, "offset": _offset},
            timeout=25,
        )
        updates = resp.json().get("result", [])
        return updates
    except Exception as e:
        log.error(f"[Bot] getUpdates error: {e}")
        return []


def handle_update(update: dict) -> None:
    global _offset
    _offset = update.get("update_id", 0) + 1
    msg  = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    if not text:
        return

    conn = init_db()
    try:
        if text.startswith("/cl_"):
            job_id = text[4:].strip()
            cl = get_cover_letter(conn, job_id)
            _tg_post(f"📄 <b>Cover Letter</b>\n\n{cl[:3800]}" if cl else f"❌ No cover letter for <code>{job_id}</code>")

        elif text.startswith("/applied_"):
            job_id = text[9:].strip()
            update_job_status(conn, job_id, "Applied")
            try:
                from sheets.client import update_job_status_sheets
                update_job_status_sheets(job_id, "Applied")
            except Exception:
                pass
            fu = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
            _tg_post(f"✅ <b>Applied logged!</b>\n📅 Follow-up: {fu}")

        elif text.startswith("/interview_"):
            job_id = text[11:].strip()
            update_job_status(conn, job_id, "Interviewing")
            job = get_job_by_id(conn, job_id)
            co = job.get("company", "the company") if job else "the company"
            _tg_post(f"🎯 <b>Interviewing logged!</b>\n💡 Tip for {co}: Prepare STAR stories on RAG, LLM fine-tuning, and prod ML scale.")

        elif text.startswith("/reject_"):
            job_id = text[8:].strip()
            update_job_status(conn, job_id, "Rejected")
            _tg_post(f"💪 Rejected logged. On to the next one! 🚀")

        elif text.startswith("/skip_"):
            job_id = text[6:].strip()
            update_job_status(conn, job_id, "Skipped")
            _tg_post(f"🚫 Skipped.")

        elif text == "/top5":
            jobs = get_top_jobs(conn, n=5, status="New")
            if not jobs:
                _tg_post("📭 No new matches yet.")
            else:
                lines = ["🏆 <b>Top 5 Matches</b>\n"]
                for i, j in enumerate(jobs, 1):
                    lines.append(f"{i}. <b>{j.get('match_score',0)}/100</b> — {j.get('job_title','N/A')}\n   🏢 {j.get('company','?')} | {j.get('location','?')}")
                _tg_post("\n".join(lines))

        elif text == "/status":
            send_status(get_db_stats(conn), _get_uptime())

        elif text in ("/start", "/help"):
            _tg_post(
                "🤖 <b>JobRadar AI v5.0</b>\n\n"
                "/top5 — Top new matches\n"
                "/status — Scanner health\n"
                "/cl_&lt;id&gt; — Cover letter\n"
                "/applied_&lt;id&gt; — Mark applied\n"
                "/interview_&lt;id&gt; — Interviewing\n"
                "/reject_&lt;id&gt; — Rejected\n"
                "/skip_&lt;id&gt; — Skip job"
            )
    except Exception as e:
        log.error(f"[Bot] Error: {e}")
    finally:
        conn.close()


def run_bot_polling():
    if not BOT_TOKEN:
        log.warning("[Bot] No token — disabled.")
        return
    log.info("🤖 Bot polling started → @KotaKarthik_bot")
    while True:
        try:
            for update in _get_updates():
                handle_update(update)
        except Exception as e:
            log.error(f"[Bot] Polling error: {e}")
        time.sleep(1)


def start_bot_in_background():
    t = threading.Thread(target=run_bot_polling, daemon=True, name="TelegramBot")
    t.start()
    return t
