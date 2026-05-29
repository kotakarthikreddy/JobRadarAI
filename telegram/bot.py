"""
bot.py — Telegram bot (single-instance polling).
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from db.storage import init_db, get_job_by_id, update_job_status, get_top_jobs, get_db_stats
from telegram.alerts import send_status
from telegram.config import register_chat_id, get_chat_id

log = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_offset = 0
_start_time = datetime.now(timezone.utc)
_LOCK = Path("data/bot_polling.lock")
_POLLING = False


def _send_to(chat_id: str, text: str, parse_mode: str = "") -> bool:
    if not BOT_TOKEN or not chat_id:
        return False
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        log.error("[Bot] send failed: %s", e)
        return False


def _get_uptime() -> str:
    delta = datetime.now(timezone.utc) - _start_time
    h, rem = divmod(int(delta.total_seconds()), 3600)
    return f"{h}h {rem // 60}m"


def _load_offset() -> None:
    global _offset
    p = Path("data/bot_offset.txt")
    if p.exists():
        try:
            _offset = int(p.read_text(encoding="utf-8").strip())
        except Exception:
            _offset = 0


def _save_offset() -> None:
    Path("data/bot_offset.txt").write_text(str(_offset), encoding="utf-8")


def _get_updates():
    global _offset
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"timeout": 20, "offset": _offset},
            timeout=25,
        )
        data = resp.json()
        if not data.get("ok"):
            log.warning("[Bot] getUpdates: %s", data)
            return []
        return data.get("result", [])
    except Exception as e:
        log.error("[Bot] getUpdates error: %s", e)
        return []


def handle_update(update: dict) -> None:
    global _offset
    _offset = update.get("update_id", 0) + 1
    _save_offset()

    msg = update.get("message") or update.get("edited_message") or {}
    text = (msg.get("text") or "").strip()
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id", ""))

    if chat_id:
        register_chat_id(chat_id)

    if not text:
        return

    conn = init_db()
    try:
        if text.startswith("/applied_"):
            job_id = text[9:].strip()
            update_job_status(conn, job_id, "Applied")
            fu = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
            _send_to(chat_id, f"Applied logged. Follow-up: {fu}")

        elif text.startswith("/skip_"):
            job_id = text[6:].strip()
            update_job_status(conn, job_id, "Skipped")
            _send_to(chat_id, "Skipped.")

        elif text == "/top5":
            jobs = get_top_jobs(conn, n=5, status="New")
            if not jobs:
                _send_to(chat_id, "No new ML jobs yet. Scanner runs every 5 min.")
            else:
                lines = ["Top 5 ML jobs:\n"]
                for i, j in enumerate(jobs, 1):
                    lines.append(
                        f"{i}. {j.get('match_score', 0)}/100 — {j.get('job_title', 'N/A')}\n"
                        f"   {j.get('company', '?')} | {j.get('location', '?')}\n"
                        f"   {j.get('job_url', '')}"
                    )
                _send_to(chat_id, "\n".join(lines))

        elif text == "/status":
            stats = get_db_stats(conn)
            _send_to(
                chat_id,
                f"JobRadar Live\n"
                f"Uptime: {_get_uptime()}\n"
                f"ML jobs tracked: {stats.get('total_seen', 0)}\n"
                f"Applied: {stats.get('applied', 0)}",
            )

        elif text in ("/start", "/help", "/reset", "/myid"):
            _send_to(
                chat_id,
                f"JobRadar AI connected.\n\n"
                f"Your chat ID: {chat_id}\n"
                f"(saved — alerts will come here)\n\n"
                f"Commands:\n"
                f"/top5 — best new ML jobs\n"
                f"/status — scanner stats\n"
                f"/applied_<id> — mark applied\n"
                f"/skip_<id> — skip job",
            )

    except Exception as e:
        log.error("[Bot] Error: %s", e)
        _send_to(chat_id, f"Error: {e}")
    finally:
        conn.close()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock() -> bool:
    global _POLLING
    _LOCK.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK.exists():
        try:
            old_pid = int(_LOCK.read_text(encoding="utf-8").strip())
            if _pid_alive(old_pid):
                log.info("[Bot] Another instance polling (pid %s) — skipping.", old_pid)
                return False
        except Exception:
            pass
    _LOCK.write_text(str(os.getpid()), encoding="utf-8")
    _POLLING = True
    return True


def run_bot_polling():
    if not BOT_TOKEN:
        log.warning("[Bot] No token — disabled.")
        return
    if not _acquire_lock():
        return
    _load_offset()
    # Clear any webhook so getUpdates works
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=10)
    except Exception:
        pass
    log.info("[Bot] Polling started -> @KotaKarthik_bot")
    while True:
        try:
            for update in _get_updates():
                handle_update(update)
        except Exception as e:
            log.error("[Bot] Polling error: %s", e)
        time.sleep(1)


def start_bot_in_background():
    t = threading.Thread(target=run_bot_polling, daemon=True, name="TelegramBot")
    t.start()
    return t
