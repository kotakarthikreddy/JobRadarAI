"""Sync all existing job_tracker rows from SQLite → Google Sheets (one-time backfill)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from db.storage import init_db, get_all_jobs
from sheets.client import _get_sheet, _ensure_headers, JT_HEADERS, SEEN_HEADERS, log_seen_id
from db.storage import make_url_hash, make_title_hash

def main():
    conn = init_db()
    jobs = get_all_jobs(conn)
    conn.close()

    if not jobs:
        print("No jobs in DB to sync.")
        return

    sh = _get_sheet()
    if not sh:
        print("ERROR: Cannot connect to Google Sheets. Check GOOGLE_CREDS_JSON.")
        return

    # Get or create Job Tracker worksheet
    try:
        ws = sh.worksheet("Job Tracker")
    except Exception:
        ws = sh.add_worksheet("Job Tracker", rows=1000, cols=len(JT_HEADERS) + 2)
    _ensure_headers(ws, JT_HEADERS)

    # Get existing job_ids in sheet to avoid duplicates
    existing_ids = set()
    try:
        col_a = ws.col_values(1)  # job_id column
        existing_ids = set(col_a[1:])  # skip header
    except Exception:
        pass

    print(f"DB has {len(jobs)} jobs. Sheet already has {len(existing_ids)} rows.")

    synced = 0
    for job in jobs:
        job_id = str(job.get("job_id", ""))
        if job_id in existing_ids:
            continue

        row = [
            job_id,
            str(job.get("detected_at", "")),
            str(job.get("company", "")),
            str(job.get("job_title", "")),
            str(job.get("location", "")),
            str(job.get("remote_friendly", "")),
            int(job.get("match_score", 0)),
            str(job.get("verdict", "")),
            str(job.get("h1b_sponsor", "")),
            str(job.get("salary_estimate", "")),
            str(job.get("job_url", "")),
            str(job.get("status", "New")),
            str(job.get("applied_date", "") or ""),
            str(job.get("follow_up_date", "") or ""),
            str(job.get("notes", "") or ""),
            str(job.get("cover_letter", "") or "")[:500],
            str(job.get("ats_type", "")),
        ]

        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
            synced += 1
            if synced % 10 == 0:
                print(f"  Synced {synced} jobs...")
            # Rate limit: 60 writes/min for free tier
            time.sleep(1.2)
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                print(f"  Rate limited at {synced} rows. Waiting 60s...")
                time.sleep(60)
                try:
                    ws.append_row(row, value_input_option="USER_ENTERED")
                    synced += 1
                except Exception:
                    pass
            else:
                print(f"  Error: {e}")
                break

    print(f"\nDone! Synced {synced} new jobs to Google Sheets.")


if __name__ == "__main__":
    main()
