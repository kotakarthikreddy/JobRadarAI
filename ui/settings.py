"""Settings — Telegram setup and scan control only."""
import asyncio
import os
import streamlit as st

from scanner.orchestrator import run_scan
from telegram.alerts import _tg_post
from telegram.config import get_chat_id, register_chat_id, telegram_configured


def show_settings():
    st.title("Settings")

    st.subheader("Telegram alerts")
    st.markdown("Bot: [@KotaKarthik_bot](https://t.me/KotaKarthik_bot)")

    chat_id = get_chat_id()
    if chat_id:
        st.success(f"Connected — chat ID `{chat_id}`")
    else:
        st.error("Not connected yet")

    st.markdown(
        "**Option A (easiest):** Message [@userinfobot](https://t.me/userinfobot) → copy your numeric ID → paste below.\n\n"
        "**Option B:** Message @KotaKarthik_bot with `/start` while the scanner is running."
    )

    new_id = st.text_input("Your Telegram Chat ID", value=chat_id or "", placeholder="e.g. 123456789")
    if st.button("Save & Test", type="primary"):
        if not new_id.strip():
            st.warning("Enter your chat ID first.")
        else:
            register_chat_id(new_id.strip())
            ok = _tg_post("JobRadar AI connected. You will get new ML job alerts here.")
            if ok:
                st.success("Saved and test message sent! Check Telegram.")
            else:
                st.error("Saved locally but message failed. Double-check the chat ID.")

    st.divider()
    st.subheader("Scanner")
    if st.button("Run scan now", use_container_width=True):
        with st.spinner("Scanning career pages..."):
            try:
                result = asyncio.run(run_scan())
                st.success(
                    f"Done — fetched {result.get('total', 0)} jobs, "
                    f"{result.get('alerted', 0)} alerts sent."
                )
            except Exception as e:
                st.error(str(e))

    st.divider()
    st.caption("Optional env vars in `.env`: GEMINI_API_KEY, GROQ_API_KEY, GOOGLE_CREDS_JSON")
