"""
app.py — JobRadar AI v5.0 — Main Streamlit Entry Point
Premium dark-mode UI combining best of all 6 projects.
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone

import streamlit as st

# ── Page config (MUST be first Streamlit call) ─────────────────────
st.set_page_config(
    page_title="JobRadar AI v5.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "JobRadar AI v5.0 — Built for Karthik | OPT → H1B Track"},
)

# ── Load environment ───────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Setup paths ────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/jobradar.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Imports ────────────────────────────────────────────────────────
from db.storage import init_db, get_all_jobs, get_db_stats, update_job_status
from scanner.orchestrator import run_scan, get_scanner_stats
from telegram.bot import start_bot_in_background

# ─────────────────────────────────────────────────────────────────
# GLOBAL CSS — Dark premium theme
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Root variables */
:root {
  --bg-primary:   #0a0a0f;
  --bg-card:      #111118;
  --bg-card-hover:#16161f;
  --border:       #1e1e2e;
  --accent:       #6366f1;
  --accent-glow:  rgba(99,102,241,0.25);
  --green:        #10b981;
  --yellow:       #f59e0b;
  --red:          #ef4444;
  --text-primary: #f1f5f9;
  --text-muted:   #64748b;
  --text-dim:     #334155;
}

/* Global */
.stApp { background: var(--bg-primary); font-family: 'Inter', sans-serif; color: var(--text-primary); }
section[data-testid="stSidebar"] { background: #0d0d14; border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }
h1,h2,h3,h4 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif; }

/* Sidebar logo */
.sidebar-logo {
  display:flex; align-items:center; gap:10px;
  padding:16px 0; margin-bottom:8px;
}
.sidebar-logo-icon {
  font-size:28px; background:var(--accent); border-radius:10px;
  width:44px; height:44px; display:flex; align-items:center; justify-content:center;
}
.sidebar-logo-text { font-size:16px; font-weight:700; letter-spacing:-0.3px; }
.sidebar-logo-sub { font-size:11px; color:var(--text-muted); margin-top:2px; }

/* Metric cards */
.metric-card {
  background:var(--bg-card); border:1px solid var(--border);
  border-radius:16px; padding:20px 24px; position:relative; overflow:hidden;
  transition:all 0.2s;
}
.metric-card:hover { border-color:var(--accent); background:var(--bg-card-hover); }
.metric-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg, var(--accent), transparent);
}
.metric-value { font-size:2rem; font-weight:800; line-height:1; color:var(--text-primary); }
.metric-label { font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;
                letter-spacing:0.5px; margin-top:6px; }
.metric-delta { font-size:0.75rem; margin-top:4px; font-weight:600; }
.delta-up   { color:var(--green); }
.delta-down { color:var(--red); }

/* Job card */
.job-card {
  background:var(--bg-card); border:1px solid var(--border);
  border-radius:16px; padding:24px; margin-bottom:16px;
  transition:all 0.25s; cursor:default;
}
.job-card:hover {
  border-color:var(--accent); background:var(--bg-card-hover);
  transform:translateY(-2px);
  box-shadow:0 8px 32px var(--accent-glow);
}
.job-card-header { display:flex; justify-content:space-between; align-items:flex-start; }
.company-avatar {
  width:48px; height:48px; border-radius:12px;
  background:linear-gradient(135deg, var(--accent), #8b5cf6);
  display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:20px; color:white; flex-shrink:0;
}
.job-title { font-size:1.1rem; font-weight:700; color:var(--text-primary); margin:0 0 4px; }
.job-company { font-size:0.9rem; color:var(--text-muted); margin:0; }

/* Score ring */
.score-ring {
  width:76px; height:88px; border-radius:12px;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  font-weight:800; text-align:center; flex-shrink:0;
}
.score-ring.strong { background:linear-gradient(135deg,#065f46,#047857); }
.score-ring.apply  { background:linear-gradient(135deg,#1e3a5f,#1d4ed8); }
.score-ring.gaps   { background:linear-gradient(135deg,#78350f,#b45309); }
.score-ring.skip   { background:linear-gradient(135deg,#1f1f2e,#374151); }
.score-value { font-size:1.6rem; line-height:1; color:white; }
.score-label { font-size:0.55rem; text-transform:uppercase; letter-spacing:0.8px;
               color:rgba(255,255,255,0.8); margin-top:3px; }

/* Badges */
.badge {
  display:inline-flex; align-items:center; gap:4px;
  padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600;
}
.badge-h1b    { background:#052e16; color:#34d399; border:1px solid #065f46; }
.badge-remote { background:#0c1a40; color:#93c5fd; border:1px solid #1e3a8a; }
.badge-new    { background:#2d1b69; color:#c4b5fd; border:1px solid #4c1d95; }
.badge-warn   { background:#451a03; color:#fbbf24; border:1px solid #92400e; }

/* Meta row */
.meta-row { display:flex; flex-wrap:wrap; gap:12px; margin-top:12px; }
.meta-item { display:flex; align-items:center; gap:5px; font-size:0.85rem; color:var(--text-muted); }

/* Divider */
.hr { border:none; border-top:1px solid var(--border); margin:16px 0; }

/* Status pills */
.status-new          { color:#c4b5fd; background:#2d1b69; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.status-applied      { color:#34d399; background:#052e16; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.status-interviewing { color:#fbbf24; background:#451a03; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.status-rejected     { color:#f87171; background:#450a0a; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }

/* Scanner status banner */
.scanner-online  { background:#052e16; border:1px solid #065f46; border-radius:10px;
                   padding:10px 16px; color:#34d399; font-weight:600; font-size:0.85rem; }
.scanner-offline { background:#1c1c1c; border:1px solid #374151; border-radius:10px;
                   padding:10px 16px; color:#9ca3af; font-weight:600; font-size:0.85rem; }

/* Stremlit override */
div.stButton > button {
  border-radius:8px; font-weight:600; font-size:0.85rem; border:none;
  transition:all 0.2s;
}
div.stButton > button:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(99,102,241,0.3); }
div[data-testid="stMetricValue"] { font-size:1.8rem !important; font-weight:800 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────
if "scanner_running" not in st.session_state:
    st.session_state.scanner_running = False
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False
if "scan_log" not in st.session_state:
    st.session_state.scan_log = []

# Start Telegram bot once
if not st.session_state.bot_started:
    start_bot_in_background()
    st.session_state.bot_started = True


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">🎯</div>
      <div>
        <div class="sidebar-logo-text">JobRadar AI</div>
        <div class="sidebar-logo-sub">v5.0 · OPT → H1B Track</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "🔍 Job Feed", "📝 Applications", "⚙️ Scanner", "👤 Profile"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick scan button
    if st.button("⚡ Run Scan Now", type="primary", use_container_width=True):
        with st.spinner("Scanning all sources…"):
            try:
                result = asyncio.run(run_scan())
                st.success(f"✅ Found {result.get('alerted', 0)} new alerts!")
            except Exception as e:
                st.error(f"Scan error: {e}")

    st.markdown("---")
    conn = init_db()
    stats = get_db_stats(conn)
    conn.close()
    st.caption("📊 Quick Stats")
    st.metric("Total Seen", stats.get("total_seen", 0))
    st.metric("Alerted", stats.get("total_alerted", 0))
    st.metric("Applied", stats.get("applied", 0))
    st.markdown("---")
    st.caption("🤖 @KotaKarthik_bot active")


# ─────────────────────────────────────────────────────────────────
# PAGE ROUTING
# ─────────────────────────────────────────────────────────────────
from ui.dashboard import show_dashboard
from ui.job_feed import show_job_feed
from ui.applications import show_applications
from ui.scanner_control import show_scanner
from ui.profile import show_profile

if page == "🏠 Dashboard":
    show_dashboard()
elif page == "🔍 Job Feed":
    show_job_feed()
elif page == "📝 Applications":
    show_applications()
elif page == "⚙️ Scanner":
    show_scanner()
elif page == "👤 Profile":
    show_profile()
