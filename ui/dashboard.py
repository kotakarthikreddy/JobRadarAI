"""ui/dashboard.py — Stats dashboard page"""
import streamlit as st
import pandas as pd
from datetime import datetime
from db.storage import init_db, get_all_jobs, get_db_stats

def show_dashboard():
    st.markdown("## 🏠 Dashboard")

    conn  = init_db()
    stats = get_db_stats(conn)
    jobs  = get_all_jobs(conn)
    conn.close()

    # ── Metric row ──────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{stats.get("total_seen",0)}</div>
        <div class="metric-label">Jobs Scanned</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{stats.get("total_alerted",0)}</div>
        <div class="metric-label">Alerts Sent</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{stats.get("applied",0)}</div>
        <div class="metric-label">Applied</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{stats.get("interviewing",0)}</div>
        <div class="metric-label">Interviewing</div></div>""", unsafe_allow_html=True)
    with c5:
        top = stats.get("top_match", {})
        score = top.get("match_score", 0) if top else 0
        st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{score}</div>
        <div class="metric-label">Top Match /100</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not jobs:
        st.info("🔍 No jobs scanned yet. Click **⚡ Run Scan Now** in the sidebar to start!")
        return

    df = pd.DataFrame(jobs)

    # ── Charts ──────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📊 Match Score Distribution")
        if "match_score" in df.columns and df["match_score"].sum() > 0:
            hist = df["match_score"].value_counts().sort_index()
            st.bar_chart(hist, color="#6366f1")
        else:
            st.caption("No scored jobs yet.")

    with col2:
        st.markdown("#### 🏢 Top Companies")
        if "company" in df.columns:
            top_co = df["company"].value_counts().head(10)
            st.bar_chart(top_co, color="#10b981")

    # ── Recent jobs table ────────────────────────────────────────
    st.markdown("#### 🕐 Recent Detections")
    display_cols = [c for c in ["detected_at","company","job_title","match_score","verdict","status","job_url"] if c in df.columns]
    if display_cols:
        st.dataframe(
            df[display_cols].head(20),
            use_container_width=True,
            column_config={
                "job_url": st.column_config.LinkColumn("Apply Link"),
                "match_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            },
        )
