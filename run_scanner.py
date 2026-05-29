"""run_scanner.py — Standalone scanner runner (no Streamlit required).
Run this to scan in the background: python run_scanner.py
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/jobradar.log"),
    ],
)
log = logging.getLogger("jobradar")

from db.storage import init_db
from scanner.orchestrator import run_scan
from telegram.bot import start_bot_in_background
from telegram.alerts import send_crash_alert, send_status
from db.storage import get_db_stats


def _validate():
    """Fail fast on missing critical config."""
    errors = []
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
        errors.append("At least one AI key required: GEMINI_API_KEY or GROQ_API_KEY")
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        errors.append("TELEGRAM_BOT_TOKEN not set — alerts won't be sent")
    if not os.getenv("TELEGRAM_CHAT_ID"):
        errors.append("TELEGRAM_CHAT_ID not set — alerts won't be sent")
    for e in errors:
        log.warning(f"⚠️  {e}")
    return True   # warnings only, not fatal


async def continuous_scan():
    """Run scans in a loop every SCAN_INTERVAL_MINUTES minutes."""
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "5"))

    log.info("=" * 60)
    log.info("🎯 JobRadar AI v5.0 — Starting continuous scan")
    log.info(f"   Interval: every {interval} minutes")
    log.info(f"   Min score: {os.getenv('MIN_MATCH_SCORE', '60')}")
    log.info(f"   H1B only: {os.getenv('H1B_ONLY', 'true')}")
    log.info("=" * 60)

    scan_count = 0
    while True:
        scan_count += 1
        try:
            result = await run_scan()
            log.info(
                f"✅ Scan #{scan_count} done | "
                f"Alerted: {result.get('alerted',0)} | "
                f"Elapsed: {result.get('elapsed_s',0)}s"
            )

            # Send status summary every 10 scans
            if scan_count % 10 == 0:
                conn = init_db()
                send_status(get_db_stats(conn), f"{scan_count * interval}m")
                conn.close()

        except KeyboardInterrupt:
            log.info("Stopped by user.")
            break
        except Exception as e:
            log.exception(f"SCAN ERROR: {e}")
            send_crash_alert(str(e))

        log.info(f"⏳ Sleeping {interval} minutes until next scan…")
        await asyncio.sleep(interval * 60)


if __name__ == "__main__":
    _validate()
    start_bot_in_background()
    log.info("🤖 Telegram bot started → @KotaKarthik_bot")

    try:
        asyncio.run(continuous_scan())
    except KeyboardInterrupt:
        log.info("👋 JobRadar AI stopped.")
