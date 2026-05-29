"""Create Job Tracker / Seen IDs / Stats Dashboard tabs with headers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from sheets.client import JT_HEADERS, SEEN_HEADERS, _get_sheet, _ensure_headers


def main():
    sh = _get_sheet()
    if not sh:
        print("Set GOOGLE_CREDS_JSON in .env (service account JSON) and share the sheet with that email.")
        sys.exit(1)
    for name, headers in [
        ("Job Tracker", JT_HEADERS),
        ("Seen IDs", SEEN_HEADERS),
        ("Stats Dashboard", ["date", "jobs_scanned", "jobs_alerted", "applied", "interviews", "avg_match_score"]),
    ]:
        try:
            ws = sh.worksheet(name)
        except Exception:
            ws = sh.add_worksheet(name, rows=1000, cols=len(headers) + 2)
        _ensure_headers(ws, headers)
        print(f"OK: {name}")
    print("Sheets ready:", os.getenv("GOOGLE_SHEET_ID"))


if __name__ == "__main__":
    main()
