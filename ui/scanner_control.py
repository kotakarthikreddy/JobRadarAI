"""ui/scanner_control.py — Scanner control & monitoring"""
import asyncio
import streamlit as st
from datetime import datetime, timezone
from scanner.orchestrator import run_scan, get_scanner_stats
from db.storage import init_db, get_db_stats
from ai.scorer import usage_report


def show_scanner():
    stats = get_scanner_stats()
    conn = init_db()
    db_stats = get_db_stats(conn)
    ai_rep = usage_report(conn)
    conn.close()

    # ── Live status bar ──────────────────────────────────────────
    uptime_str = ""
    if stats.get("start_time"):
        delta = datetime.now(timezone.utc) - stats["start_time"]
        h, rem = divmod(int(delta.total_seconds()), 3600)
        uptime_str = f"{h}h {rem // 60}m"

    st.markdown(f"""
    <div class="scanner-bar">
        <div class="scanner-dot"></div>
        <div class="scanner-text">
            <b>JobRadar AI Active</b> &nbsp;·&nbsp;
            Scans: {stats.get('scans', 0)} &nbsp;·&nbsp;
            Fetched: {stats.get('total_fetched', 0)} &nbsp;·&nbsp;
            Alerts: {stats.get('alerted', 0)} &nbsp;·&nbsp;
            Uptime: {uptime_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Controls ─────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">🚀 Manual Scan</div>', unsafe_allow_html=True)
        if st.button("⚡ Run Full Scan", type="primary", use_container_width=True):
            with st.spinner("Scanning all sources in parallel…"):
                try:
                    result = asyncio.run(run_scan())
                    st.success(
                        f"✅ Done in {result.get('elapsed_s', 0)}s\n\n"
                        f"Fetched: {result.get('total', 0)} · "
                        f"Filtered: {result.get('filtered', 0)} · "
                        f"Duped: {result.get('duped', 0)} · "
                        f"Alerted: {result.get('alerted', 0)}"
                    )
                except Exception as e:
                    st.error(f"Scan failed: {str(e)[:200]}")

    with col2:
        st.markdown('<div class="section-header">📊 Database</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div class="metric-card" style="padding:14px;">
                <div class="metric-value purple" style="font-size:1.5rem;">{db_stats.get('total_seen', 0)}</div>
                <div class="metric-label">Total Seen</div>
            </div>
            <div class="metric-card" style="padding:14px;">
                <div class="metric-value green" style="font-size:1.5rem;">{db_stats.get('seen_today', 0)}</div>
                <div class="metric-label">Today</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── AI Usage ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">🤖 AI Provider Usage (Today)</div>', unsafe_allow_html=True)
    st.code(ai_rep, language="text")

    # ── Sources monitored ────────────────────────────────────────
    st.markdown('<div class="section-header">📡 Sources Monitored</div>', unsafe_allow_html=True)

    from config.companies import TIER1_GREENHOUSE, TIER1_ASHBY, TIER2_WORKDAY
    sources = [
        ("🌿 Greenhouse", len(TIER1_GREENHOUSE)),
        ("🔷 Ashby", len(TIER1_ASHBY)),
        ("🏗️ Workday", len(TIER2_WORKDAY)),
        ("📦 Amazon", 1),
        ("🌐 Remotive", 1),
        ("🏠 RemoteOK", 1),
        ("🟠 YC/HN", 1),
        ("📋 H1B Feed", 1),
        ("📡 JobSpy", 2),
    ]
    total = sum(s[1] for s in sources)

    cols = st.columns(4)
    for i, (name, count) in enumerate(sources):
        with cols[i % 4]:
            st.markdown(f"""
            <div class="metric-card" style="padding:14px;">
                <div style="font-size:1.3rem;font-weight:800;color:#a78bfa;">{count}</div>
                <div class="metric-label">{name}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"<div style='text-align:center;color:#64748b;font-size:0.8rem;margin-top:8px;'>Total: <b>{total}</b> company endpoints</div>", unsafe_allow_html=True)

    # ── Log viewer ───────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Recent Logs</div>', unsafe_allow_html=True)
    try:
        with open("data/jobradar.log", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-40:]
        st.code("".join(lines), language="text")
    except FileNotFoundError:
        st.caption("Log file appears after first scan.")

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
