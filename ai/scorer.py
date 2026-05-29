"""
scorer.py — AI scoring engine for JobRadar AI v5.0
Provider chain: Groq (primary) → OpenRouter (secondary) → Gemini (tertiary)
Uses the v5 scoring rubric from the system prompt.
"""

import json
import logging
import os
import re
import sqlite3
import time
from typing import Optional

from db.storage import get_ai_count, increment_ai_count
from config.candidate import RESUME_TEXT, SCORING_RUBRIC

log = logging.getLogger(__name__)

PROVIDER_LIMITS = {
    "groq":       14000,  # buffer under 14,400/day
    "openrouter": 180,    # buffer under 200/day
    "gemini":     240,    # buffer under 250/day
}

FALLBACK_SCORE = {
    "match_score":     50,
    "verdict":         "APPLY WITH GAPS",
    "verdict_emoji":   "⚡",
    "top_strengths":   [],
    "skill_gaps":      [],
    "h1b_sponsor":     False,
    "salary_estimate": "Unknown",
    "apply_urgency":   "Unknown",
    "time_badge":      "",
    "insider_tip":     "Review manually — AI scoring unavailable.",
    "cover_letter":    "",
    "provider":        "fallback",
}


# ─────────────────────────────────────────────────────────────────
# PROMPT BUILDER (v5 rubric from system prompt)
# ─────────────────────────────────────────────────────────────────

def build_scoring_prompt(job: dict) -> str:
    desc    = (job.get("description") or "")[:3500]
    posted  = job.get("posted", "Unknown")
    resume  = RESUME_TEXT.strip()[:4000]

    return f"""You are an elite ML career coach and technical recruiter with 10 years FAANG hiring experience.

CANDIDATE: Karthik — Senior ML/AI Engineer
Skills: Python, PyTorch, TensorFlow, LangChain, RAG, MLflow, Spark, Kafka,
        AWS SageMaker/Bedrock/Lambda, FastAPI, Docker, LLM fine-tuning, LoRA, distributed training
Experience: TCS → Mr. Cooper → Vertraus Inc (current, AI Engineer)
Education: M.S. CS UNT 2025, B.Tech CS & Engineering (AI) VIT
Visa: OPT → H1B track

RESUME:
{resume}

JOB TO ANALYZE:
Title:       {job.get("title", "")}
Company:     {job.get("company", "")}
Location:    {job.get("location", "")}
Posted:      {posted}
Description: {desc}

SCORING RUBRIC:
- Skills match    → {SCORING_RUBRIC["skills_match"]} pts (how many required skills match?)
- Seniority match → {SCORING_RUBRIC["seniority_match"]} pts (senior/staff level?)
- Domain match    → {SCORING_RUBRIC["domain_match"]} pts (ML/AI/LLM focused?)
- Company quality → {SCORING_RUBRIC["company_quality"]} pts (FAANG/tier-1 startup?)
- Visa friendly   → {SCORING_RUBRIC["visa_friendly"]} pts (remote ok + H1B sponsor history?)

VERDICT RULES:
80-100 → STRONG APPLY 🔥
65-79  → APPLY ✅
50-64  → APPLY WITH GAPS ⚡
< 50   → SKIP (return score but set verdict to SKIP)

RETURN ONLY THIS JSON — no markdown, no preamble, no backticks:
{{
  "match_score": 85,
  "verdict": "STRONG APPLY",
  "verdict_emoji": "🔥",
  "top_strengths": ["strength 1", "strength 2"],
  "skill_gaps": ["gap 1"],
  "h1b_sponsor": true,
  "salary_estimate": "$165k–$195k",
  "apply_urgency": "HIGH",
  "time_badge": "⏱️ Posted recently — apply today",
  "insider_tip": "One company-specific tip for Karthik.",
  "cover_letter": "Dear Hiring Team at {job.get('company','')},...",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1"]
}}"""


# ─────────────────────────────────────────────────────────────────
# JSON PARSER
# ─────────────────────────────────────────────────────────────────

def parse_response(raw: str) -> Optional[dict]:
    try:
        text = re.sub(r"```json\s*|```\s*", "", raw, flags=re.IGNORECASE).strip()
        # Try to extract the JSON object
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group(0)
        result = json.loads(text)
        # Validate required keys
        if "match_score" not in result:
            return None
        result["match_score"]   = max(0, min(100, int(float(result.get("match_score", 0)))))
        result["top_strengths"] = list(result.get("top_strengths", []))[:5]
        result["skill_gaps"]    = list(result.get("skill_gaps", []))[:5]
        result["matched_skills"]= list(result.get("matched_skills", []))[:8]
        result["missing_skills"]= list(result.get("missing_skills", []))[:5]
        result["cover_letter"]  = str(result.get("cover_letter", ""))
        return result
    except Exception as e:
        log.debug(f"JSON parse failed: {e} | raw[:120]: {raw[:120]}")
        return None


# ─────────────────────────────────────────────────────────────────
# GROQ — Primary (14,400/day free)
# ─────────────────────────────────────────────────────────────────

_groq_client = None

def score_with_groq(prompt: str, conn: sqlite3.Connection) -> Optional[dict]:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    if get_ai_count(conn, "groq") >= PROVIDER_LIMITS["groq"]:
        log.warning("[Groq] Daily limit reached.")
        return None
    global _groq_client
    try:
        from groq import Groq
        if _groq_client is None:
            _groq_client = Groq(api_key=api_key)
        resp = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,
        )
        raw    = resp.choices[0].message.content.strip()
        result = parse_response(raw)
        if result:
            result["provider"] = "Groq / Llama-3.3-70B"
            count = increment_ai_count(conn, "groq")
            log.info(f"  [Groq] score={result['match_score']} | calls={count}")
            return result
    except Exception as e:
        s = str(e)
        if "429" in s or "rate_limit" in s.lower():
            log.warning("[Groq] Rate limit — sleeping 3s")
            time.sleep(3)
        else:
            log.warning(f"[Groq] Error: {s[:120]}")
    return None


# ─────────────────────────────────────────────────────────────────
# OPENROUTER — Secondary (200/day free)
# ─────────────────────────────────────────────────────────────────

def score_with_openrouter(prompt: str, conn: sqlite3.Connection) -> Optional[dict]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return None
    if get_ai_count(conn, "openrouter") >= PROVIDER_LIMITS["openrouter"]:
        log.warning("[OpenRouter] Daily limit reached.")
        return None
    try:
        import requests as req
        resp = req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization":  f"Bearer {api_key}",
                "Content-Type":   "application/json",
                "HTTP-Referer":   "https://github.com/jobradar-ai",
                "X-Title":        "JobRadar AI v5",
            },
            json={
                "model":       "meta-llama/llama-3.3-70b-instruct:free",
                "messages":    [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens":  800,
            },
            timeout=25,
        )
        resp.raise_for_status()
        raw    = resp.json()["choices"][0]["message"]["content"].strip()
        result = parse_response(raw)
        if result:
            result["provider"] = "OpenRouter / Llama-3.3-70B"
            count = increment_ai_count(conn, "openrouter")
            log.info(f"  [OpenRouter] score={result['match_score']} | calls={count}")
            return result
    except Exception as e:
        s = str(e)
        if "429" in s:
            log.warning("[OpenRouter] Rate limit — sleeping 60s")
            time.sleep(60)
        else:
            log.warning(f"[OpenRouter] Error: {s[:120]}")
    return None


# ─────────────────────────────────────────────────────────────────
# GEMINI — Tertiary + Primary for cover letters (free tier)
# ─────────────────────────────────────────────────────────────────

_gemini_client = None

def score_with_gemini(prompt: str, conn: sqlite3.Connection) -> Optional[dict]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    if get_ai_count(conn, "gemini") >= PROVIDER_LIMITS["gemini"]:
        log.warning("[Gemini] Quota hit.")
        return None
    global _gemini_client
    try:
        from google import genai
        if _gemini_client is None:
            _gemini_client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_SCORER_MODEL", "gemini-1.5-flash")
        resp  = _gemini_client.models.generate_content(model=model, contents=prompt)
        result = parse_response(resp.text.strip())
        if result:
            result["provider"] = f"Gemini / {model}"
            count = increment_ai_count(conn, "gemini")
            log.info(f"  [Gemini] score={result['match_score']} | calls={count}")
            return result
    except Exception as e:
        s = str(e)
        if "429" in s or "quota" in s.lower():
            log.warning("[Gemini] Quota — retrying with gemini-1.5-flash after 8s")
            time.sleep(8)
            try:
                resp = _gemini_client.models.generate_content(
                    model="gemini-1.5-flash", contents=prompt
                )
                result = parse_response(resp.text.strip())
                if result:
                    result["provider"] = "Gemini / gemini-1.5-flash"
                    increment_ai_count(conn, "gemini")
                    return result
            except Exception:
                pass
        else:
            log.warning(f"[Gemini] Error: {s[:120]}")
    return None


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def score_job(job: dict, conn: sqlite3.Connection) -> Optional[dict]:
    """
    Score a job using provider fallback chain: Groq → OpenRouter → Gemini.
    Returns full score dict or FALLBACK_SCORE on error.
    """
    prompt = build_scoring_prompt(job)

    # Spec: Gemini 1.5/2.0 Flash primary; Groq/OpenRouter as fallbacks
    for name, fn in [("gemini", score_with_gemini), ("groq", score_with_groq), ("openrouter", score_with_openrouter)]:
        result = fn(prompt, conn)
        if result is not None:
            return result

    log.warning("All AI providers failed — using fallback score.")
    return FALLBACK_SCORE.copy()


def usage_report(conn: sqlite3.Connection) -> str:
    g   = get_ai_count(conn, "groq")
    o   = get_ai_count(conn, "openrouter")
    gem = get_ai_count(conn, "gemini")
    return (
        f"AI usage today: Groq={g}/{PROVIDER_LIMITS['groq']} | "
        f"OpenRouter={o}/{PROVIDER_LIMITS['openrouter']} | "
        f"Gemini={gem}/{PROVIDER_LIMITS['gemini']}"
    )
