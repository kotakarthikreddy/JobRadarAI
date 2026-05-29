"""run_scanner.py — Standalone scanner runner (no Streamlit required)."""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from config.logging_setup import setup_logging
from telegram.config import get_chat_id, telegram_configured

log = setup_logging("jobradar")
os.makedirs("data", exist_ok=True)

from db.storage import init_db, get_db_stats
from scanner.orchestrator import run_scan
from telegram.bot import start_bot_in_background
from telegram.alerts import send_crash_alert, send_status


def _validate() -> None:
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
        log.warning("No AI key set — local rule-based scoring will be used.")
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        log.warning("TELEGRAM_BOT_TOKEN not set — alerts disabled.")
    if not get_chat_id():
        log.warning("TELEGRAM_CHAT_ID not set — message @KotaKarthik_bot /start to auto-configure.")
    elif telegram_configured():
        log.info("Telegram alerts configured (chat_id=%s)", get_chat_id()[:4] + "...")


async def continuous_scan():
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "5"))
    log.info("JobRadar AI v5.0 — continuous scan every %s min", interval)

    scan_count = 0
    while True:
        scan_count += 1
        try:
            result = await run_scan()
            log.info(
                "Scan #%s done | Alerted: %s | Elapsed: %ss",
                scan_count,
                result.get("alerted", 0),
                result.get("elapsed_s", 0),
            )
            if scan_count % 10 == 0 and telegram_configured():
                conn = init_db()
                send_status(get_db_stats(conn), f"{scan_count * interval}m")
                conn.close()
        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break
        except Exception as e:
            log.exception("SCAN ERROR: %s", e)
            if telegram_configured():
                send_crash_alert(str(e))

        log.info("Sleeping %s minutes until next scan...", interval)
        await asyncio.sleep(interval * 60)


if __name__ == "__main__":
    _validate()
    start_bot_in_background()
    log.info("Telegram bot started -> @KotaKarthik_bot")
    try:
        asyncio.run(continuous_scan())
    except KeyboardInterrupt:
        log.info("JobRadar AI stopped.")
