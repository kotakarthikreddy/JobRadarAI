"""
cover_letter.py — Gemini-powered cover letter generator for JobRadar AI v5.0
"""

import logging
import os
from typing import Optional

from config.candidate import RESUME_TEXT, CANDIDATE_NAME

log = logging.getLogger(__name__)

_gemini_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except Exception as e:
        log.error(f"[CoverLetter] Gemini init failed: {e}")
        return None


def generate_cover_letter(job: dict, score_result: dict) -> str:
    """
    Generate a 3-paragraph tailored cover letter using Gemini 2.0 Flash.
    Returns empty string on failure (caller uses fallback).
    """
    # Return cached version if scorer already produced one
    existing = score_result.get("cover_letter", "")
    if existing and len(existing) > 200:
        return existing

    client = _get_gemini()
    if not client:
        return _fallback_cover_letter(job)

    title   = job.get("title", "")
    company = job.get("company", "")
    desc    = (job.get("description", "") or "")[:2000]
    strengths = ", ".join(score_result.get("top_strengths", [])[:3]) or "AI/ML engineering"

    prompt = f"""Write a concise, compelling 3-paragraph cover letter for {CANDIDATE_NAME} applying to:

Role: {title}
Company: {company}
Job Description (excerpt): {desc[:1500]}

Candidate background:
{RESUME_TEXT[:2500]}

Key strengths for this role: {strengths}

Instructions:
- Paragraph 1: Hook — why THIS company and THIS role excite Karthik specifically (reference real products/tech)
- Paragraph 2: Proof — 2-3 concrete achievements (with metrics) from resume that directly map to this role
- Paragraph 3: Close — express enthusiasm, mention OPT/H1B readiness matter-of-factly, call to action

Keep it under 300 words. Professional but not robotic. No cliches like "I am writing to express my interest."
Start directly with "Dear Hiring Team at {company},"
"""

    try:
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        resp  = client.models.generate_content(model=model, contents=prompt)
        cl    = resp.text.strip()
        if len(cl) > 100:
            log.info(f"[CoverLetter] Generated {len(cl)} chars for {title} @ {company}")
            return cl
    except Exception as e:
        log.warning(f"[CoverLetter] Gemini failed: {e}")

    return _fallback_cover_letter(job)


def _fallback_cover_letter(job: dict) -> str:
    """Rule-based cover letter when AI is unavailable."""
    title   = job.get("title", "this role")
    company = job.get("company", "your company")
    return f"""Dear Hiring Team at {company},

I'm excited to apply for the {title} position. With 3+ years building production-grade ML systems — including RAG pipelines processing 500K+ annual transactions at Mr. Cooper, real-time fraud detection at 50K+ transactions/minute at TCS, and LLM-powered enterprise applications — I'm confident I can deliver immediate impact in this role.

My expertise in PyTorch, LangChain, AWS SageMaker, and MLOps directly aligns with what you're building at {company}. I've shipped systems achieving 91% accuracy on 800K+ records, reduced latency by 40%, and saved $1.2M+ annually. I'm on OPT with H1B cap-gap protection through 2026 and am seeking an employer who can sponsor long-term.

I'd welcome the opportunity to discuss how my background maps to {company}'s technical challenges. Thank you for your consideration.

Best regards,
Karthik Kota
kotakarthik.ai@gmail.com | LinkedIn | Portfolio
"""
