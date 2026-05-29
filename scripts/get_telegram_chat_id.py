"""Print your Telegram chat ID after you send /start to @KotaKarthik_bot."""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not token:
    print("Set TELEGRAM_BOT_TOKEN in .env first.")
    sys.exit(1)

resp = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates",
    params={"limit": 20},
    timeout=15,
)
data = resp.json()
if not data.get("ok"):
    print("API error:", data)
    sys.exit(1)

ids = set()
for u in data.get("result", []):
    msg = u.get("message") or u.get("edited_message") or {}
    chat = msg.get("chat") or {}
    if chat.get("id"):
        ids.add((chat["id"], chat.get("username"), chat.get("first_name")))

if not ids:
    print("No messages yet. Open Telegram → @KotaKarthik_bot → send /start")
    print("Then run this script again.")
    sys.exit(0)

print("Add one of these to .env as TELEGRAM_CHAT_ID:\n")
for cid, user, name in ids:
    print(f"  TELEGRAM_CHAT_ID={cid}  # @{user or ''} {name or ''}")
