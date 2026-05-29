"""
storage.py — SQLite storage layer for JobRadar AI v5.0
Replaces seen_jobs.json + Excel + scan_history.tsv with a single DB.

Tables:
  seen_jobs    — dedup store (3-layer: job_id, url_hash, title_hash)
  job_tracker  — full job record (mirrors Google Sheets Job Tracker)
  ai_usage     — daily AI call counters per provider
  cover_letters — stored cover letters per job_id
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional


def _get_db_path() -> str:
    path = os.getenv("DB_PATH", "data/jobradar.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> sqlite3.Connection:
    """Create all tables on first run. Safe to call on every startup."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            job_id      TEXT,
            url_hash    TEXT,
            title_hash  TEXT,
            title       TEXT,
            company     TEXT,
            source      TEXT,
            score       INTEGER DEFAULT 0,
            logged_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            PRIMARY KEY (job_id)
        );

        CREATE TABLE IF NOT EXISTS job_tracker (
            job_id          TEXT PRIMARY KEY,
            detected_at     TEXT,
            company         TEXT,
            job_title       TEXT,
            location        TEXT,
            remote_friendly TEXT,
            match_score     INTEGER DEFAULT 0,
            verdict         TEXT,
            h1b_sponsor     TEXT,
            salary_estimate TEXT,
            job_url         TEXT,
            status          TEXT DEFAULT 'New',
            applied_date    TEXT,
            follow_up_date  TEXT,
            notes           TEXT,
            cover_letter    TEXT,
            ats_type        TEXT,
            source          TEXT,
            wave1_sent      INTEGER DEFAULT 0,
            wave2_sent      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ai_usage (
            provider    TEXT PRIMARY KEY,
            calls_today INTEGER DEFAULT 0,
            reset_date  TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_seen_url    ON seen_jobs(url_hash);
        CREATE INDEX IF NOT EXISTS idx_seen_title  ON seen_jobs(title_hash);
        CREATE INDEX IF NOT EXISTS idx_seen_logged ON seen_jobs(logged_at);
        CREATE INDEX IF NOT EXISTS idx_tracker_score ON job_tracker(match_score DESC);
        CREATE INDEX IF NOT EXISTS idx_tracker_status ON job_tracker(status);
    """)
    conn.commit()
    return conn


# ─────────────────────────────────────────────────────────────────
# HASHING
# ─────────────────────────────────────────────────────────────────

def make_url_hash(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def make_title_hash(title: str, company: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────
# 3-LAYER DEDUP
# ─────────────────────────────────────────────────────────────────

def is_new_job(conn: sqlite3.Connection, job: dict) -> bool:
    """Return True only if the job passes ALL 3 dedup layers."""
    job_id   = str(job.get("job_id", "") or job.get("id", ""))
    url      = str(job.get("url", ""))
    title    = str(job.get("title", ""))
    company  = str(job.get("company", ""))

    # Layer 1 — Job ID (fastest)
    if job_id:
        row = conn.execute("SELECT 1 FROM seen_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row:
            return False

    # Layer 2 — URL hash
    if url:
        uhash = make_url_hash(url)
        row = conn.execute("SELECT 1 FROM seen_jobs WHERE url_hash=?", (uhash,)).fetchone()
        if row:
            return False

    # Layer 3 — Fuzzy title+company (exact hash within 30 days)
    if title and company:
        thash  = make_title_hash(title, company)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        row    = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE title_hash=? AND logged_at >= ?",
            (thash, cutoff)
        ).fetchone()
        if row:
            return False

    return True


def mark_job_seen(conn: sqlite3.Connection, job: dict, score: int = 0) -> None:
    job_id  = str(job.get("job_id", "") or job.get("id", "") or make_url_hash(job.get("url", "")))
    url     = str(job.get("url", ""))
    title   = str(job.get("title", ""))
    company = str(job.get("company", ""))

    conn.execute(
        """INSERT OR IGNORE INTO seen_jobs
           (job_id, url_hash, title_hash, title, company, source, score)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            make_url_hash(url) if url else "",
            make_title_hash(title, company) if title else "",
            title, company,
            str(job.get("source", "")),
            score,
        )
    )
    conn.commit()


def prune_old_jobs(conn: sqlite3.Connection, days: int = 30) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur    = conn.execute("DELETE FROM seen_jobs WHERE logged_at < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


# ─────────────────────────────────────────────────────────────────
# JOB TRACKER
# ─────────────────────────────────────────────────────────────────

def upsert_job(conn: sqlite3.Connection, job: dict, score_result: dict) -> None:
    """Insert or update a job in the tracker table."""
    job_id   = str(job.get("job_id", "") or make_url_hash(job.get("url", "")))
    now      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    salary   = score_result.get("salary_estimate", "")
    verdict  = score_result.get("verdict", "")
    score    = int(score_result.get("match_score", 0))
    cl       = score_result.get("cover_letter", "")
    h1b      = "✅ Yes" if job.get("h1b_verified") else "❓ Unknown"

    conn.execute("""
        INSERT INTO job_tracker
            (job_id, detected_at, company, job_title, location, remote_friendly,
             match_score, verdict, h1b_sponsor, salary_estimate, job_url,
             status, cover_letter, ats_type, source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(job_id) DO UPDATE SET
            match_score    = excluded.match_score,
            verdict        = excluded.verdict,
            salary_estimate = excluded.salary_estimate,
            cover_letter   = excluded.cover_letter
    """, (
        job_id, now,
        job.get("company", ""), job.get("title", ""), job.get("location", ""),
        "Yes" if "remote" in str(job.get("location", "")).lower() else "Unknown",
        score, verdict, h1b, salary, job.get("url", ""),
        "New", cl, job.get("ats_type", ""), job.get("source", ""),
    ))
    conn.commit()


def get_job_by_id(conn: sqlite3.Connection, job_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM job_tracker WHERE job_id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def update_job_status(conn: sqlite3.Connection, job_id: str, status: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if status == "Applied":
        follow_up = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        conn.execute(
            "UPDATE job_tracker SET status=?, applied_date=?, follow_up_date=? WHERE job_id=?",
            (status, now, follow_up, job_id)
        )
    else:
        conn.execute("UPDATE job_tracker SET status=? WHERE job_id=?", (status, job_id))
    conn.commit()


def get_top_jobs(conn: sqlite3.Connection, n: int = 5, status: str = "New") -> list:
    rows = conn.execute(
        "SELECT * FROM job_tracker WHERE status=? ORDER BY match_score DESC LIMIT ?",
        (status, n)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_jobs(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT * FROM job_tracker ORDER BY detected_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_cover_letter(conn: sqlite3.Connection, job_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT cover_letter FROM job_tracker WHERE job_id=?", (job_id,)
    ).fetchone()
    return row["cover_letter"] if row else None


# ─────────────────────────────────────────────────────────────────
# AI USAGE COUNTERS
# ─────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_ai_count(conn: sqlite3.Connection, provider: str) -> int:
    today = _today_utc()
    row   = conn.execute(
        "SELECT calls_today, reset_date FROM ai_usage WHERE provider=?", (provider,)
    ).fetchone()
    if not row or row["reset_date"] != today:
        return 0
    return row["calls_today"]


def increment_ai_count(conn: sqlite3.Connection, provider: str) -> int:
    today = _today_utc()
    conn.execute(
        """INSERT INTO ai_usage (provider, calls_today, reset_date) VALUES (?,1,?)
           ON CONFLICT(provider) DO UPDATE SET
               calls_today = CASE WHEN reset_date=? THEN calls_today+1 ELSE 1 END,
               reset_date  = ?""",
        (provider, today, today, today),
    )
    conn.commit()
    return get_ai_count(conn, provider)


# ─────────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────────

def get_db_stats(conn: sqlite3.Connection) -> dict:
    today = _today_utc()
    total       = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
    seen_today  = conn.execute("SELECT COUNT(*) FROM seen_jobs WHERE logged_at >= ?", (today,)).fetchone()[0]
    alerted     = conn.execute("SELECT COUNT(*) FROM seen_jobs WHERE score >= 60").fetchone()[0]
    applied     = conn.execute("SELECT COUNT(*) FROM job_tracker WHERE status='Applied'").fetchone()[0]
    interviewing = conn.execute("SELECT COUNT(*) FROM job_tracker WHERE status='Interviewing'").fetchone()[0]
    top_row     = conn.execute("SELECT company, match_score FROM job_tracker ORDER BY match_score DESC LIMIT 1").fetchone()
    return {
        "total_seen":     total,
        "seen_today":     seen_today,
        "total_alerted":  alerted,
        "applied":        applied,
        "interviewing":   interviewing,
        "top_match":      dict(top_row) if top_row else {},
    }
