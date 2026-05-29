"""
change_detection.py — Detect genuinely new jobs between poll snapshots.
"""

import hashlib
import json
import os
import time
from typing import Any


def _snapshot_path(name: str) -> str:
    os.makedirs("data", exist_ok=True)
    return os.path.join("data", f"snapshot_{name}.json")


def load_snapshot(name: str) -> set[str]:
    path = _snapshot_path(name)
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("job_ids", []))
    except Exception:
        return set()


def save_snapshot(name: str, job_ids: set[str]) -> None:
    path = _snapshot_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"job_ids": sorted(job_ids), "updated_at": time.time()}, f)


def diff_jobs(
    source: str,
    current_jobs: list[dict],
    id_key: str = "job_id",
) -> dict[str, Any]:
    """
    Return only jobs whose IDs were not in the previous snapshot.
    Reposts with new IDs are treated as new (per spec).
    """
    start = time.monotonic()
    prev = load_snapshot(source)
    new_jobs = []
    current_ids: set[str] = set()

    for job in current_jobs:
        jid = str(job.get(id_key, "") or job.get("id", ""))
        if not jid:
            jid = hashlib.md5(str(job.get("url", "")).encode()).hexdigest()[:16]
            job["job_id"] = jid
        current_ids.add(jid)
        if jid not in prev:
            new_jobs.append(job)

    removed = [{"job_id": x} for x in prev - current_ids]
    save_snapshot(source, current_ids)

    return {
        "new_jobs": new_jobs,
        "removed_jobs": removed,
        "unchanged": len(new_jobs) == 0 and len(removed) == 0,
        "scan_ms": int((time.monotonic() - start) * 1000),
    }


def html_title_hash(titles: list[str]) -> str:
    """MD5 of sorted job titles for HTML-only career pages."""
    normalized = sorted(t.strip().lower() for t in titles if t.strip())
    return hashlib.md5("|".join(normalized).encode()).hexdigest()
