"""
app.py — JobRadar AI v5.0 — Premium Streamlit UI
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
    page_title="JobRadar AI v5.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
# GLOBAL CSS — Premium dark theme
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Base ─────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #0a0f1a 0%, #0f172a 100%);
    color: #e2e8f0;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #0f172a 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.15);
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── Sidebar branding ─────────────────────────────── */
.sidebar-brand {
    text-align: center;
    padding: 24px 0 16px;
    border-bottom: 1px solid rgba(99,102,241,0.2);
    margin-bottom: 20px;
}
.sidebar-brand h1 {
    font-size: 1.6rem; font-weight: 900;
    background: linear-gradient(135deg, #6366f1, #a78bfa, #6366f1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; letter-spacing: -0.5px;
}
.sidebar-brand p {
    font-size: 0.7rem; color: #64748b !important;
    text-transform: uppercase; letter-spacing: 2px; margin: 4px 0 0;
}

/* ── Metric cards ─────────────────────────────────── */
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }
.metric-card {
    background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}
.metric-card:hover { border-color: rgba(99,102,241,0.5); transform: translateY(-2px); box-shadow: 0 8px 32px rgba(99,102,241,0.1); }
.metric-icon { font-size: 1.8rem; margin-bottom: 8px; }
.metric-value { font-size: 2.2rem; font-weight: 900; color: #f1f5f9; line-height: 1; }
.metric-value.purple { color: #a78bfa; }
.metric-value.green { color: #34d399; }
.metric-value.blue { color: #60a5fa; }
.metric-value.amber { color: #fbbf24; }
.metric-value.rose { color: #fb7185; }
.metric-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 6px; font-weight: 600; }

/* ── Job cards ────────────────────────────────────── */
.job-card {
    background: linear-gradient(135deg, rgba(30,41,59,0.6), rgba(15,23,42,0.8));
    border: 1px solid rgba(51,65,85,0.6);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}
.job-card:hover { border-color: rgba(99,102,241,0.4); box-shadow: 0 4px 24px rgba(99,102,241,0.08); }
.job-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.job-card-body { flex: 1; }
.company-avatar {
    width: 48px; height: 48px; border-radius: 12px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; font-weight: 800; color: white; flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}
.job-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; line-height: 1.3; }
.job-company { font-size: 0.88rem; color: #94a3b8; margin-bottom: 10px; font-weight: 500; }
.meta-row { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
.meta-item { font-size: 0.78rem; color: #64748b; display: flex; align-items: center; gap: 4px; }

/* ── Score ring ───────────────────────────────────── */
.score-ring {
    width: 76px; height: 76px; border-radius: 50%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    flex-shrink: 0; position: relative;
}
.score-ring::before {
    content: ''; position: absolute; inset: 0; border-radius: 50%;
    border: 3px solid currentColor; opacity: 0.2;
}
.score-ring::after {
    content: ''; position: absolute; inset: 0; border-radius: 50%;
    border: 3px solid transparent; border-top-color: currentColor;
}
.score-ring.strong { color: #10b981; background: rgba(16,185,129,0.08); }
.score-ring.apply  { color: #6366f1; background: rgba(99,102,241,0.08); }
.score-ring.gaps   { color: #f59e0b; background: rgba(245,158,11,0.08); }
.score-ring.skip   { color: #ef4444; background: rgba(239,68,68,0.08); }
.score-value { font-size: 1.5rem; font-weight: 900; line-height: 1; }
.score-label { font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; font-weight: 700; }

/* ── Badges ───────────────────────────────────────── */
.badge-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.68rem; font-weight: 600;
    border: 1px solid;
}
.badge-h1b    { background: rgba(16,185,129,0.1); color: #34d399; border-color: rgba(16,185,129,0.3); }
.badge-remote { background: rgba(99,102,241,0.1); color: #818cf8; border-color: rgba(99,102,241,0.3); }
.badge-new    { background: rgba(245,158,11,0.1); color: #fbbf24; border-color: rgba(245,158,11,0.3); }
.badge-applied { background: rgba(16,185,129,0.1); color: #34d399; border-color: rgba(16,185,129,0.3); }
.badge-skip   { background: rgba(239,68,68,0.1); color: #fb7185; border-color: rgba(239,68,68,0.3); }

/* ── Section headers ──────────────────────────────── */
.section-header {
    font-size: 1.2rem; font-weight: 800; color: #f1f5f9;
    margin: 32px 0 16px; padding-bottom: 12px;
    border-bottom: 1px solid rgba(99,102,241,0.15);
    display: flex; align-items: center; gap: 10px;
}

/* ── Scanner status bar ───────────────────────────── */
.scanner-bar {
    background: linear-gradient(90deg, rgba(16,185,129,0.08), rgba(99,102,241,0.08));
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 12px;
    padding: 14px 20px;
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 24px;
}
.scanner-dot { width: 10px; height: 10px; border-radius: 50%; background: #10b981; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.scanner-text { font-size: 0.82rem; color: #94a3b8; font-weight: 500; }
.scanner-text b { color: #10b981; }

/* ── Tables ───────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* ── Buttons ──────────────────────────────────────── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
}

/* ── Tabs ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
}

/* ── Hide defaults ────────────────────────────────── */
#MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# INIT
# ══════════════════════════════════════════════════════════════════
from db.storage import init_db, get_db_stats, get_ml_jobs, rescore_all_jobs
from telegram.config import get_chat_id, telegram_configured
from telegram.bot import start_bot_in_background

if "bot_started" not in st.session_state:
    start_bot_in_background()
    st.session_state.bot_started = True

if "rescored" not in st.session_state:
    conn = init_db()
    ml = get_ml_jobs(conn)
    if ml and all(int(j.get("match_score") or 0) <= 50 for j in ml[:5]):
        rescore_all_jobs(conn)
    st.session_state.rescored = True
    conn.close()

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <h1>🎯 JobRadar AI</h1>
        <p>ML/AI · OPT→H1B · v5.0</p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "NAV",
        ["🏠 Dashboard", "🔍 Job Feed", "📝 Applications", "⚙️ Scanner", "👤 Profile"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    conn = init_db()
    stats = get_db_stats(conn)
    ml_count = len(get_ml_jobs(conn))
    conn.close()

    st.markdown(f"""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:0 4px;">
        <div style="text-align:center; padding:12px 8px; background:rgba(99,102,241,0.08); border-radius:10px; border:1px solid rgba(99,102,241,0.15);">
            <div style="font-size:1.4rem; font-weight:800; color:#a78bfa;">{ml_count}</div>
            <div style="font-size:0.6rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;">ML Jobs</div>
        </div>
        <div style="text-align:center; padding:12px 8px; background:rgba(16,185,129,0.08); border-radius:10px; border:1px solid rgba(16,185,129,0.15);">
            <div style="font-size:1.4rem; font-weight:800; color:#34d399;">{stats.get('applied',0)}</div>
            <div style="font-size:0.6rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Applied</div>
        </div>
        <div style="text-align:center; padding:12px 8px; background:rgba(245,158,11,0.08); border-radius:10px; border:1px solid rgba(245,158,11,0.15);">
            <div style="font-size:1.4rem; font-weight:800; color:#fbbf24;">{stats.get('total_alerted',0)}</div>
            <div style="font-size:0.6rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Alerted</div>
        </div>
        <div style="text-align:center; padding:12px 8px; background:rgba(251,113,133,0.08); border-radius:10px; border:1px solid rgba(251,113,133,0.15);">
            <div style="font-size:1.4rem; font-weight:800; color:#fb7185;">{stats.get('interviewing',0)}</div>
            <div style="font-size:0.6rem; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Interviews</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if telegram_configured():
        st.markdown('<div style="text-align:center;padding:6px;background:rgba(16,185,129,0.1);border-radius:8px;border:1px solid rgba(16,185,129,0.2);font-size:0.75rem;color:#34d399;font-weight:600;">✅ Telegram Live</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;padding:6px;background:rgba(245,158,11,0.1);border-radius:8px;border:1px solid rgba(245,158,11,0.2);font-size:0.75rem;color:#fbbf24;font-weight:600;">⚠️ Telegram Not Set</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡ Run Scan Now", use_container_width=True, type="primary"):
        import asyncio
        from scanner.orchestrator import run_scan
        with st.spinner("Scanning all sources…"):
            try:
                result = asyncio.run(run_scan())
                st.success(f"✅ {result.get('alerted',0)} alerts | {result.get('total',0)} fetched")
            except Exception as e:
                st.error(str(e)[:100])

# ══════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    from ui.dashboard import show_dashboard
    show_dashboard()
elif page == "🔍 Job Feed":
    from ui.job_feed import show_job_feed
    show_job_feed()
elif page == "📝 Applications":
    from ui.applications import show_applications
    show_applications()
elif page == "⚙️ Scanner":
    from ui.scanner_control import show_scanner
    show_scanner()
elif page == "👤 Profile":
    from ui.profile import show_profile
    show_profile()
