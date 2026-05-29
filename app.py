"""
app.py — JobRadar AI — simple job list UI
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(__file__))
os.makedirs("data", exist_ok=True)

st.set_page_config(
    page_title="JobRadar AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from db.storage import init_db, get_db_stats, get_ml_jobs, rescore_all_jobs
from telegram.config import get_chat_id, register_chat_id, telegram_configured

# One-time rescore if jobs stuck at score 50
if "rescored" not in st.session_state:
    conn = init_db()
    ml = get_ml_jobs(conn)
    if ml and all(int(j.get("match_score") or 0) <= 50 for j in ml[:5]):
        rescore_all_jobs(conn)
    st.session_state.rescored = True
    conn.close()

with st.sidebar:
    st.title("JobRadar AI")
    st.caption("ML/AI jobs · H1B sponsors")

    page = st.radio("Menu", ["Jobs", "Settings"], label_visibility="collapsed")

    conn = init_db()
    stats = get_db_stats(conn)
    ml_count = len(get_ml_jobs(conn))
    conn.close()

    st.metric("ML jobs", ml_count)
    st.metric("Applied", stats.get("applied", 0))

    if telegram_configured():
        st.success("Telegram connected")
    else:
        st.warning("Telegram not set — go to Settings")

from ui.jobs import show_jobs
from ui.settings import show_settings

if page == "Jobs":
    show_jobs()
else:
    show_settings()
