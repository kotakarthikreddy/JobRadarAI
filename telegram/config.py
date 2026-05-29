"""Telegram chat ID resolution: .env -> data/telegram_chat.json -> auto-save from bot."""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_CHAT_FILE = Path("data/telegram_chat.json")
_ENV_FILE = Path(".env")


def _read_saved() -> str:
    if not _CHAT_FILE.exists():
        return ""
    try:
        return str(json.loads(_CHAT_FILE.read_text(encoding="utf-8")).get("chat_id", "")).strip()
    except Exception:
        return ""


def _write_env(chat_id: str) -> None:
    if not _ENV_FILE.exists():
        return
    text = _ENV_FILE.read_text(encoding="utf-8")
    if re.search(r"^TELEGRAM_CHAT_ID=.*$", text, flags=re.MULTILINE):
        text = re.sub(r"^TELEGRAM_CHAT_ID=.*$", f"TELEGRAM_CHAT_ID={chat_id}", text, flags=re.MULTILINE)
    else:
        text = text.rstrip() + f"\nTELEGRAM_CHAT_ID={chat_id}\n"
    _ENV_FILE.write_text(text, encoding="utf-8")


def register_chat_id(chat_id: str) -> None:
    chat_id = str(chat_id).strip()
    if not chat_id:
        return
    os.environ["TELEGRAM_CHAT_ID"] = chat_id
    _CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CHAT_FILE.write_text(json.dumps({"chat_id": chat_id}, indent=2), encoding="utf-8")
    _write_env(chat_id)


def get_chat_id() -> str:
    cid = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if cid:
        return cid
    saved = _read_saved()
    if saved:
        os.environ["TELEGRAM_CHAT_ID"] = saved
        return saved
    return ""


def telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip() and get_chat_id())
