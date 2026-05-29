"""ui/profile.py — Profile & settings page"""
import streamlit as st
import os
from config.candidate import (
    CANDIDATE_NAME, CANDIDATE_EMAIL, CANDIDATE_LOCATION,
    CANDIDATE_VISA, CANDIDATE_SALARY_RANGE, EXACT_ROLES, CORE_SKILLS
)

def show_profile():
    st.markdown("## 👤 Profile & Settings")

    tab1, tab2, tab3 = st.tabs(["👤 Candidate Info", "🔑 API Keys", "🤖 Telegram Status"])

    with tab1:
        st.subheader("Candidate Profile")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Name", CANDIDATE_NAME, disabled=True)
            st.text_input("Email", CANDIDATE_EMAIL, disabled=True)
            st.text_input("Location", CANDIDATE_LOCATION, disabled=True)
        with c2:
            st.text_input("Visa Status", CANDIDATE_VISA, disabled=True)
            st.text_input("Salary Target", CANDIDATE_SALARY_RANGE, disabled=True)

        st.markdown("---")
        st.subheader("Target Roles")
        st.info("These roles are hardcoded in `config/candidate.py`. Edit that file to change them.")
        for r in EXACT_ROLES[:10]:
            st.markdown(f"• {r.title()}")

        st.markdown("---")
        st.subheader("Core Skills (used for keyword matching)")
        st.write(", ".join(sorted(CORE_SKILLS)))

    with tab2:
        st.subheader("API Configuration")
        st.info("These values are loaded from your `.env` file. Edit `.env` to update them.")

        keys = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
            "GOOGLE_SHEET_ID": os.getenv("GOOGLE_SHEET_ID", ""),
        }
        for k, v in keys.items():
            masked = ("✅ " + v[:6] + "…" + v[-4:]) if v and len(v) > 10 else ("⚠️ Not set" if not v else "✅ Set")
            st.text_input(k, masked, disabled=True)

        st.markdown("---")
        st.subheader("Min Match Score")
        min_score = int(os.getenv("MIN_MATCH_SCORE", "60"))
        st.metric("Current threshold", f"{min_score}/100")
        st.caption("Change `MIN_MATCH_SCORE` in `.env` to adjust")

    with tab3:
        st.subheader("Telegram Bot Status")
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8481347460:AAGh94HRDgOwvSEJJt0B58WFl-vxtlGYO5I")
        chat_id   = os.getenv("TELEGRAM_CHAT_ID", "")

        if bot_token:
            st.success(f"✅ Bot connected: @KotaKarthik_bot")
        else:
            st.error("❌ Bot token not set in .env")

        if chat_id:
            st.success(f"✅ Chat ID configured: {chat_id[:4]}…")
        else:
            st.warning(
                "⚠️ **TELEGRAM_CHAT_ID not set!**\n\n"
                "1. Open Telegram\n"
                "2. Message [@userinfobot](https://t.me/userinfobot)\n"
                "3. Copy the ID number it gives you\n"
                "4. Add to `.env`: `TELEGRAM_CHAT_ID=your_id_here`"
            )

        st.markdown("---")
        st.subheader("Test Alert")
        if st.button("📱 Send Test Message", type="primary"):
            try:
                from telegram.alerts import _tg_post
                ok = _tg_post("🎯 <b>JobRadar AI v5.0 is live!</b>\n\nYour scanner is configured and ready. Good luck Karthik! 🚀")
                if ok:
                    st.success("✅ Test message sent! Check your Telegram.")
                else:
                    st.error("❌ Failed to send. Check TELEGRAM_CHAT_ID in .env")
            except Exception as e:
                st.error(f"Error: {e}")
