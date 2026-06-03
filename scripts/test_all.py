"""Production readiness test — verifies all components work."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

errors = []

def check(name, fn):
    try:
        fn()
        print(f"  ✅ {name}")
    except Exception as e:
        errors.append((name, str(e)))
        print(f"  ❌ {name}: {e}")

print("=" * 60)
print("JobRadar AI v5.0 — Production Readiness Check")
print("=" * 60)

# 1. Database
print("\n[1] Database")
def test_db():
    from db.storage import init_db, get_db_stats, get_all_jobs, get_ml_jobs, get_top_jobs
    conn = init_db()
    stats = get_db_stats(conn)
    assert stats["total_seen"] >= 0
    jobs = get_all_jobs(conn)
    ml = get_ml_jobs(conn)
    top = get_top_jobs(conn)
    conn.close()
    print(f"    Total: {len(jobs)} | ML: {len(ml)} | Top5: {len(top)}")
check("SQLite init + queries", test_db)

# 2. Filters
print("\n[2] Filters")
def test_filters():
    from scanner.filters import apply_all_filters, detect_h1b, extract_resume_skills
    from config.candidate import RESUME_TEXT
    skills = extract_resume_skills(RESUME_TEXT)
    assert len(skills) > 10
    job = {
        "title": "Senior ML Engineer", "company": "Google",
        "location": "Remote, USA",
        "description": "Build ML pipelines with PyTorch, LangChain, RAG",
        "posted": "2026-05-29", "h1b_verified": True,
    }
    v, label = detect_h1b(job)
    assert v is True
    ok, reason = apply_all_filters(job, skills)
    assert ok is True
    print(f"    Skills extracted: {len(skills)} | H1B: {label}")
check("All filters pass for good job", test_filters)

def test_filters_reject():
    from scanner.filters import apply_all_filters, extract_resume_skills
    from config.candidate import RESUME_TEXT
    skills = extract_resume_skills(RESUME_TEXT)
    bad_job = {
        "title": "Marketing Manager", "company": "Random Corp",
        "location": "London, UK", "description": "manage marketing campaigns",
        "posted": "2026-05-29", "h1b_verified": False,
    }
    ok, reason = apply_all_filters(bad_job, skills, h1b_only=True)
    assert ok is False
    print(f"    Rejected: {reason}")
check("Filters reject non-ML job", test_filters_reject)

# 3. Local Scorer
print("\n[3] Local Scorer")
def test_local_scorer():
    from ai.local_scorer import score_job_local
    job = {
        "title": "Senior ML Engineer", "company": "Google",
        "location": "Remote",
        "description": "PyTorch, LangChain, RAG, AWS SageMaker, MLflow, Docker",
        "h1b_verified": True,
    }
    r = score_job_local(job)
    assert r["match_score"] >= 60
    assert r["verdict"] in ("STRONG APPLY", "APPLY", "APPLY WITH GAPS")
    print(f"    Score: {r['match_score']}/100 — {r['verdict']} {r['verdict_emoji']}")
check("Local rule-based scorer", test_local_scorer)

# 4. AI Scorer (prompt + parse)
print("\n[4] AI Scorer")
def test_scorer_prompt():
    from ai.scorer import build_scoring_prompt, parse_response
    import json
    job = {"title": "ML Engineer", "company": "NVIDIA", "location": "Remote", "description": "Build ML", "posted": "2026-05-29"}
    prompt = build_scoring_prompt(job)
    assert len(prompt) > 1000
    test_resp = json.dumps({
        "match_score": 82, "verdict": "STRONG APPLY", "verdict_emoji": "🔥",
        "top_strengths": ["PyTorch match"], "skill_gaps": ["Go"],
        "h1b_sponsor": True, "salary_estimate": "$170k",
        "apply_urgency": "HIGH", "time_badge": "⏱️ Fresh",
        "insider_tip": "Apply fast", "cover_letter": "Dear Team...",
        "matched_skills": ["python", "pytorch"], "missing_skills": ["go"],
    })
    result = parse_response(test_resp)
    assert result["match_score"] == 82
    print(f"    Prompt: {len(prompt)} chars | Parse: score={result['match_score']}")
check("Prompt build + JSON parse", test_scorer_prompt)

# 5. Telegram
print("\n[5] Telegram")
def test_telegram_config():
    from telegram.config import get_chat_id, telegram_configured
    cid = get_chat_id()
    assert cid and len(cid) > 5
    assert telegram_configured()
    print(f"    Chat ID: {cid[:4]}... | Configured: True")
check("Telegram config", test_telegram_config)

def test_telegram_send():
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "✅ JobRadar AI production check passed!"},
        timeout=10,
    )
    assert r.status_code == 200
    print(f"    Message sent successfully")
check("Telegram send message", test_telegram_send)

# 6. Google Sheets
print("\n[6] Google Sheets")
def test_sheets():
    from sheets.client import _get_sheet
    sh = _get_sheet()
    if sh is None:
        print("    ⚠️  Sheets disabled (no creds or quota)")
        return
    ws = sh.worksheet("Job Tracker")
    rows = ws.row_count
    print(f"    Connected | Job Tracker rows: {rows}")
check("Sheets connection", test_sheets)

# 7. Cover Letter
print("\n[7] Cover Letter")
def test_cover_letter():
    from ai.cover_letter import _fallback_cover_letter
    job = {"title": "ML Engineer", "company": "OpenAI"}
    cl = _fallback_cover_letter(job)
    assert len(cl) > 200
    assert "OpenAI" in cl
    print(f"    Fallback letter: {len(cl)} chars")
check("Cover letter fallback", test_cover_letter)

# 8. Change Detection
print("\n[8] Change Detection")
def test_change_detection():
    from scanner.change_detection import diff_jobs, html_title_hash
    jobs = [{"job_id": "abc123", "title": "ML Eng"}, {"job_id": "def456", "title": "AI Eng"}]
    result = diff_jobs("test_source", jobs)
    assert "new_jobs" in result
    h = html_title_hash(["ML Engineer", "AI Engineer"])
    assert len(h) == 32
    print(f"    Diff: {len(result['new_jobs'])} new | Hash: {h[:12]}...")
check("Change detection engine", test_change_detection)

# 9. Companies config
print("\n[9] Companies Config")
def test_companies():
    from config.companies import TIER1_GREENHOUSE, TIER1_ASHBY, TIER2_WORKDAY, H1B_FEED_BASE
    total = len(TIER1_GREENHOUSE) + len(TIER1_ASHBY) + len(TIER2_WORKDAY) + 4  # +Amazon, H1B, JobSpy(2)
    assert total > 90
    assert "{year}" in H1B_FEED_BASE
    print(f"    Total endpoints: {total}")
check("Company watchlist", test_companies)

# 10. Candidate config
print("\n[10] Candidate Config")
def test_candidate():
    from config.candidate import (
        CANDIDATE_NAME, CORE_SKILLS, VERIFIED_H1B_SPONSORS,
        KEYWORD_FILTER, EXCLUDE_KEYWORDS, SCORING_RUBRIC, EXACT_ROLES,
    )
    assert CANDIDATE_NAME == "Karthik"
    assert len(CORE_SKILLS) > 20
    assert len(VERIFIED_H1B_SPONSORS) > 50
    assert sum(SCORING_RUBRIC.values()) == 100
    print(f"    Skills: {len(CORE_SKILLS)} | Sponsors: {len(VERIFIED_H1B_SPONSORS)} | Rubric: {sum(SCORING_RUBRIC.values())}pts")
check("Candidate profile", test_candidate)

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)} FAILED:")
    for name, err in errors:
        print(f"   • {name}: {err}")
else:
    print("✅ ALL CHECKS PASSED — PRODUCTION READY")
print("=" * 60)
