"""run_scanner.py — Production-grade continuous scanner (no Streamlit required)."""

import asyncio
import os
import sys
import traceback

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


def _validate() -> bool:
    """Validate configuration. Returns True if minimum config is present."""
    ok = True

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
        log.warning("⚠️  No AI key set — local rule-based scoring will be used.")

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        log.warning("⚠️  TELEGRAM_BOT_TOKEN not set — alerts disabled.")
        ok = False

    if not get_chat_id():
        log.warning("⚠️  TELEGRAM_CHAT_ID not set — message @KotaKarthik_bot /start to auto-configure.")
    elif telegram_configured():
        log.info("✅ Telegram alerts configured (chat_id=%s…)", get_chat_id()[:4])

    if os.getenv("GOOGLE_CREDS_JSON"):
        log.info("✅ Google Sheets integration enabled.")
    else:
        log.info("ℹ️  Google Sheets disabled (GOOGLE_CREDS_JSON not set).")

    return ok


async def continuous_scan():
    """Main scan loop with exponential backoff on repeated failures."""
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "5"))
    log.info("=" * 60)
    log.info("🚀 JobRadar AI v5.0 — Starting continuous scan")
    log.info("   Interval: %s min | H1B only: %s | Min score: %s",
             interval, os.getenv("H1B_ONLY", "true"), os.getenv("MIN_MATCH_SCORE", "60"))
    log.info("=" * 60)

    scan_count = 0
    consecutive_errors = 0
    max_backoff = 30  # max 30 min between retries on repeated failures

    while True:
        scan_count += 1
        try:
            result = await run_scan()
            consecutive_errors = 0  # reset on success

            log.info(
                "✅ Scan #%s | Fetched: %s | Filtered: %s | Duped: %s | Alerted: %s | Time: %ss",
                scan_count,
                result.get("total", 0),
                result.get("filtered", 0),
                result.get("duped", 0),
                result.get("alerted", 0),
                result.get("elapsed_s", 0),
            )

            # Send periodic status update every 10 scans
            if scan_count % 10 == 0 and telegram_configured():
                conn = init_db()
                send_status(get_db_stats(conn), f"{scan_count * interval}m")
                conn.close()

        except KeyboardInterrupt:
            log.info("⏹️  Stopped by user (Ctrl+C).")
            break

        except Exception as e:
            consecutive_errors += 1
            log.exception("❌ SCAN ERROR #%s (consecutive: %s): %s", scan_count, consecutive_errors, e)

            if telegram_configured() and consecutive_errors <= 3:
                send_crash_alert(f"Scan #{scan_count} failed: {str(e)[:300]}")

            # Exponential backoff: 5, 10, 20, 30 min max
            if consecutive_errors >= 5:
                backoff = min(interval * (2 ** (consecutive_errors - 1)), max_backoff)
                log.warning("⚠️  %s consecutive failures — backing off %s min", consecutive_errors, backoff)
                await asyncio.sleep(backoff * 60)
                continue

        # Normal sleep between scans
        log.info("💤 Next scan in %s minutes…", interval)
        await asyncio.sleep(interval * 60)


if __name__ == "__main__":
    _validate()

    # Start Telegram bot in background thread
    start_bot_in_background()
    log.info("🤖 Telegram bot started → @KotaKarthik_bot")

    try:
        asyncio.run(continuous_scan())
    except KeyboardInterrupt:
        log.info("🛑 JobRadar AI stopped.")
    except Exception as e:
        log.critical("💀 Fatal error: %s", e)
        log.critical(traceback.format_exc())
        if telegram_configured():
            send_crash_alert(f"FATAL: {str(e)[:400]}")
        sys.exit(1)
