"""
settings.py — All environment variable configuration via pydantic-settings.
"""

import os
from functools import lru_cache
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # ── AI Providers ──────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # ── Telegram ──────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── Google Sheets ─────────────────────────────────────────────
    GOOGLE_SHEET_ID: str = "12aDfDaW4LP1s97q8CJHG0GPFb1lahRCuCIus0k5Tjho"
    GOOGLE_CREDS_JSON: str = ""  # Full JSON content of service account

    # ── Scanner Behavior ─────────────────────────────────────────
    MIN_MATCH_SCORE: int = 60
    H1B_ONLY: bool = True
    HOURS_OLD: int = 48
    SCAN_INTERVAL_MINUTES: int = 5
    REQUEST_TIMEOUT: int = 12
    MAX_CONCURRENT_REQUESTS: int = 10

    # ── Database ──────────────────────────────────────────────────
    DB_PATH: str = "data/jobradar.db"

    # ── Gemini Model ──────────────────────────────────────────────
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_SCORER_MODEL: str = "gemini-1.5-flash"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()
