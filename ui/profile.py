"""ui/profile.py — Candidate profile & configuration"""
import streamlit as st
import os
from config.candidate import (
    CANDIDATE_NAME, CANDIDATE_EMAIL, CANDIDATE_LOCATION,
    CANDIDATE_VISA, CANDIDATE_SALARY_RANGE, EXACT_ROLES, CORE_SKILLS
)
from telegram.config import get_chat_id, register_chat_id, telegram_configured
from telegram.alerts import _tg_post


def show_profile():
    st.markdown('<div class="section-header">👤 Profile & Configuration</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["👤 Candidate", "🔑 API Keys", "🤖 Telegram"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="text-align:left; padding:24px;">
                <div style="font-size:1.3rem; font-weight:800; color:#f1f5f9; margin-bottom:12px;">
                    {CANDIDATE_NAME}
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; line-height:2;">
                    📧 {CANDIDATE_EMAIL}<br>
                    📍 {CANDIDATE_LOCATION}<br>
                    🛂 {CANDIDATE_VISA}<br>
                    💰 {CANDIDATE_SALARY_RANGE}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="metric-card" style="text-align:left; padding:24px;">
                <div style="font-size:0.9rem; font-weight:700; color:#f1f5f9; margin-bottom:12px;">
                    🎯 Target Roles
                </div>
            </div>
            """, unsafe_allow_html=True)
            for r in EXACT_ROLES[:8]:
                st.markdown(f"<span style='font-size:0.8rem;color:#94a3b8;'>• {r.title()}</span>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">🛠️ Core Skills</div>', unsafe_allow_html=True)
        skills_html = " ".join(
            f'<span class="badge badge-remote" style="margin:3px;">{s}</span>'
            for s in sorted(CORE_SKILLS)
        )
        st.markdown(f'<div style="line-height:2.2;">{skills_html}</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="section-header">🔑 API Configuration</div>', unsafe_allow_html=True)
        st.caption("Values loaded from `.env` — edit that file to change them.")

        keys = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "TELEGRAM_CHAT_ID": get_chat_id(),
            "GOOGLE_SHEET_ID": os.getenv("GOOGLE_SHEET_ID", ""),
            "GOOGLE_CREDS_JSON": os.getenv("GOOGLE_CREDS_JSON", "")[:20] + "…" if os.getenv("GOOGLE_CREDS_JSON") else "",
        }

        for k, v in keys.items():
            if v and len(v) > 10:
                status = f"✅ `{v[:8]}…{v[-4:]}`"
            elif v:
                status = "✅ Set"
            else:
                status = "⚠️ Not configured"
            st.markdown(f"**{k}** → {status}")

    with tab3:
        st.markdown('<div class="section-header">🤖 Telegram Bot</div>', unsafe_allow_html=True)

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = get_chat_id()

        if bot_token and chat_id:
            st.markdown(f"""
            <div class="scanner-bar">
                <div class="scanner-dot"></div>
                <div class="scanner-text">
                    <b>Connected</b> → @KotaKarthik_bot · Chat: {chat_id[:6]}…
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Telegram not fully configured.")

        st.markdown("---")
        st.markdown("**Update Chat ID:**")
        st.caption("Message [@userinfobot](https://t.me/userinfobot) to get your numeric ID, or send /start to @KotaKarthik_bot.")

        new_id = st.text_input("Chat ID", value=chat_id or "", placeholder="e.g. 1004924254")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                if new_id.strip():
                    register_chat_id(new_id.strip())
                    st.success("Saved!")
                    st.rerun()
        with col2:
            if st.button("📱 Send Test", use_container_width=True, type="primary"):
                ok = _tg_post("🎯 JobRadar AI v5.0 is live!\n\nAlerts configured and ready. Good luck Karthik! 🚀")
                if ok:
                    st.success("✅ Check Telegram!")
                else:
                    st.error("Failed — check token & chat ID")
