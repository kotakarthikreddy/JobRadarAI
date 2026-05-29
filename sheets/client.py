"""
client.py — Google Sheets integration for JobRadar AI v5.0
Sheet 1: Job Tracker | Sheet 2: Seen IDs | Sheet 3: Stats Dashboard
"""

import json
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "12aDfDaW4LP1s97q8CJHG0GPFb1lahRCuCIus0k5Tjho")

_gc   = None
_sh   = None


def _get_sheet():
    global _gc, _sh
    if _sh is not None:
        return _sh
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_json = os.getenv("GOOGLE_CREDS_JSON", "")
        if not creds_json:
            log.warning("[Sheets] GOOGLE_CREDS_JSON not set — Sheets integration disabled.")
            return None

        creds_data = json.loads(creds_json)
        scopes     = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        _gc   = gspread.authorize(creds)
        _sh   = _gc.open_by_key(SHEET_ID)
        log.info(f"[Sheets] Connected to sheet: {SHEET_ID}")
        return _sh
    except Exception as e:
        log.error(f"[Sheets] Connection failed: {e}")
        return None


def _ensure_headers(ws, headers: list) -> None:
    """Write headers if row 1 is empty."""
    try:
        first = ws.row_values(1)
        if not first:
            ws.append_row(headers)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
# JOB TRACKER SHEET (Sheet 1)
# ─────────────────────────────────────────────────────────────────

JT_HEADERS = [
    "job_id", "detected_at", "company", "job_title", "location",
    "remote_friendly", "match_score", "verdict", "h1b_sponsor",
    "salary_estimate", "job_url", "status", "applied_date",
    "follow_up_date", "notes", "cover_letter", "ats_type",
]


def log_job_to_sheets(job: dict, score_result: dict) -> None:
    sh = _get_sheet()
    if not sh:
        return
    try:
        ws      = sh.worksheet("Job Tracker")
        _ensure_headers(ws, JT_HEADERS)

        job_id  = str(job.get("job_id", ""))
        now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        h1b     = "Yes" if job.get("h1b_verified") else "Unknown"
        cl_text = (score_result.get("cover_letter", "") or "")[:500]

        row = [
            job_id, now,
            job.get("company", ""), job.get("title", ""), job.get("location", ""),
            "Yes" if "remote" in str(job.get("location", "")).lower() else "Unknown",
            score_result.get("match_score", 0), score_result.get("verdict", ""),
            h1b, score_result.get("salary_estimate", ""), job.get("url", ""),
            "New", "", "", "", cl_text, job.get("ats_type", ""),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        log.info(f"[Sheets] Logged: {job.get('title')} @ {job.get('company')}")
    except Exception as e:
        log.error(f"[Sheets] log_job_to_sheets error: {e}")


def update_job_status_sheets(job_id: str, status: str) -> None:
    sh = _get_sheet()
    if not sh:
        return
    try:
        ws   = sh.worksheet("Job Tracker")
        cell = ws.find(job_id)
        if cell:
            ws.update_cell(cell.row, JT_HEADERS.index("status") + 1, status)
    except Exception as e:
        log.error(f"[Sheets] update_status error: {e}")


# ─────────────────────────────────────────────────────────────────
# SEEN IDs SHEET (Sheet 2)
# ─────────────────────────────────────────────────────────────────

SEEN_HEADERS = ["job_id", "url_hash", "title_hash", "logged_at"]


def log_seen_id(job_id: str, url_hash: str, title_hash: str) -> None:
    sh = _get_sheet()
    if not sh:
        return
    try:
        ws  = sh.worksheet("Seen IDs")
        _ensure_headers(ws, SEEN_HEADERS)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        ws.append_row([job_id, url_hash, title_hash, now])
    except Exception as e:
        log.error(f"[Sheets] log_seen_id error: {e}")


# ─────────────────────────────────────────────────────────────────
# STATS DASHBOARD (Sheet 3)
# ─────────────────────────────────────────────────────────────────

def update_stats_dashboard(stats: dict) -> None:
    sh = _get_sheet()
    if not sh:
        return
    try:
        ws = sh.worksheet("Stats Dashboard")
        _ensure_headers(ws, ["date", "jobs_scanned", "jobs_alerted", "applied", "avg_match_score"])
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ws.append_row([
            today,
            stats.get("total", 0),
            stats.get("alerted", 0),
            stats.get("applied", 0),
            stats.get("avg_score", 0),
        ])
    except Exception as e:
        log.error(f"[Sheets] update_stats_dashboard error: {e}")
