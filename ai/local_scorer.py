"""Rule-based job scoring when AI providers are unavailable."""
from config.candidate import CORE_SKILLS, VERIFIED_H1B_SPONSORS, KEYWORD_FILTER, SCORING_RUBRIC
from scanner.filters import _token_in_text


def _verdict(score: int) -> tuple[str, str]:
    if score >= 80:
        return "STRONG APPLY", "🔥"
    if score >= 65:
        return "APPLY", "✅"
    if score >= 50:
        return "APPLY WITH GAPS", "⚡"
    return "SKIP", "❌"


def score_job_local(job: dict) -> dict:
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    company = (job.get("company") or "").lower()
    combined = f"{title} {desc}"

    skills_pts = min(
        SCORING_RUBRIC["skills_match"],
        sum(2 for s in CORE_SKILLS if _token_in_text(s, combined)) * 4,
    )
    seniority_pts = 12 if any(k in title for k in ("senior", "staff", "lead", "principal")) else 8
    domain_pts = SCORING_RUBRIC["domain_match"] if any(k.lower() in combined for k in KEYWORD_FILTER) else 8
    company_pts = 10 if any(s in company for s in VERIFIED_H1B_SPONSORS) else 5
    visa_pts = 10 if job.get("h1b_verified") else 3

    score = min(100, skills_pts + seniority_pts + domain_pts + company_pts + visa_pts)
    verdict, emoji = _verdict(score)

    matched = [s for s in sorted(CORE_SKILLS) if _token_in_text(s, combined)][:5]
    strengths = [f"Strong match on {s}" for s in matched[:3]] or ["ML/AI domain role"]
    gaps = ["Review full JD for niche requirements"] if score < 75 else []

    return {
        "match_score": score,
        "verdict": verdict,
        "verdict_emoji": emoji,
        "top_strengths": strengths,
        "skill_gaps": gaps,
        "h1b_sponsor": bool(job.get("h1b_verified")),
        "salary_estimate": "$140k–$200k",
        "apply_urgency": "MEDIUM",
        "time_badge": "⏱️ Recently detected — review today",
        "insider_tip": f"Tailor resume to {job.get('company', 'this company')} ML stack keywords from the JD.",
        "cover_letter": "",
        "matched_skills": matched,
        "missing_skills": [],
        "provider": "local-rules",
    }
