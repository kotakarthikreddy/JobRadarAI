"""ui/scanner_control.py — Scanner control & live log page"""
import asyncio
import streamlit as st
from datetime import datetime, timezone
from scanner.orchestrator import run_scan, get_scanner_stats
from db.storage import init_db, get_db_stats
from ai.scorer import usage_report

def show_scanner():
    st.markdown("## ⚙️ Scanner Control")

    stats   = get_scanner_stats()
    conn    = init_db()
    db_stats = get_db_stats(conn)
    ai_rep  = usage_report(conn)
    conn.close()

    # ── Status banner ────────────────────────────────────────
    uptime_str = ""
    if stats.get("start_time"):
        delta = datetime.now(timezone.utc) - stats["start_time"]
        h, rem = divmod(int(delta.total_seconds()), 3600)
        uptime_str = f"{h}h {rem//60}m"

    st.markdown(f"""
    <div class="scanner-online">
      🟢 JobRadar AI v5.0 — Active &nbsp;|&nbsp;
      Scans run: {stats.get('scans', 0)} &nbsp;|&nbsp;
      Total fetched: {stats.get('total_fetched', 0)} &nbsp;|&nbsp;
      Alerts: {stats.get('alerted', 0)} &nbsp;|&nbsp;
      Uptime: {uptime_str}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Controls ────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🚀 Manual Scan")
        if st.button("⚡ Run Full Scan Now", type="primary", use_container_width=True):
            with st.spinner("🔍 Scanning all 8 sources in parallel…"):
                try:
                    result = asyncio.run(run_scan())
                    st.success(
                        f"✅ Scan complete!\n"
                        f"- Fetched: {result.get('total', 0)}\n"
                        f"- Filtered: {result.get('filtered', 0)}\n"
                        f"- Duped: {result.get('duped', 0)}\n"
                        f"- Alerted: {result.get('alerted', 0)}\n"
                        f"- Time: {result.get('elapsed_s', 0)}s"
                    )
                except Exception as e:
                    st.error(f"Scan failed: {e}")

    with c2:
        st.markdown("#### 📊 Database Stats")
        st.metric("Total jobs seen",   db_stats.get("total_seen", 0))
        st.metric("Seen today",        db_stats.get("seen_today", 0))
        st.metric("Total alerted",     db_stats.get("total_alerted", 0))

    # ── AI Usage ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🤖 AI Provider Usage (Today)")
    st.code(ai_rep)

    # ── Sources status ───────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📡 Sources Being Monitored")

    from config.companies import TIER1_GREENHOUSE, TIER1_LEVER, TIER1_ASHBY, TIER2_WORKDAY
    sources = {
        "Greenhouse": len(TIER1_GREENHOUSE),
        "Lever": len(TIER1_LEVER),
        "Ashby": len(TIER1_ASHBY),
        "Workday": len(TIER2_WORKDAY),
        "Google Careers": 1,
        "Amazon Jobs": 1,
        "H1B GitHub Feed": 1,
        "JobSpy (Indeed/Glassdoor)": 4,
    }
    total = sum(sources.values())

    cs = st.columns(4)
    for i, (src, count) in enumerate(sources.items()):
        with cs[i % 4]:
            st.markdown(f"""
            <div class="metric-card" style="padding:14px">
              <div style="font-size:1.2rem;font-weight:800">{count}</div>
              <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase">{src}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"<br>**Total companies monitored: {total}**", unsafe_allow_html=True)

    # ── Log viewer ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Scan Log")
    try:
        with open("data/jobradar.log", "r") as f:
            log_lines = f.readlines()[-60:]
        st.code("".join(log_lines), language="text")
    except FileNotFoundError:
        st.info("Log file will appear after first scan.")

    if st.button("🔄 Refresh Log"):
        st.rerun()
