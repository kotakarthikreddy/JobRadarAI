"""ui/dashboard.py — Premium stats dashboard"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from db.storage import init_db, get_all_jobs, get_db_stats


def show_dashboard():
    conn = init_db()
    stats = get_db_stats(conn)
    jobs = get_all_jobs(conn)
    conn.close()

    # ── Hero metrics ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-icon">🔍</div>
            <div class="metric-value purple">{stats.get("total_seen", 0)}</div>
            <div class="metric-label">Jobs Scanned</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value green">{stats.get("total_alerted", 0)}</div>
            <div class="metric-label">Alerts Sent</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">✅</div>
            <div class="metric-value blue">{stats.get("applied", 0)}</div>
            <div class="metric-label">Applied</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🎤</div>
            <div class="metric-value amber">{stats.get("interviewing", 0)}</div>
            <div class="metric-label">Interviewing</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🏆</div>
            <div class="metric-value rose">{stats.get("top_match", {}).get("match_score", 0) if stats.get("top_match") else 0}</div>
            <div class="metric-label">Top Score /100</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not jobs:
        st.info("🔍 No jobs scanned yet. Click **⚡ Run Scan Now** in the sidebar to start!")
        return

    df = pd.DataFrame(jobs)

    # ── Charts row ───────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">📊 Score Distribution</div>', unsafe_allow_html=True)
        if "match_score" in df.columns and df["match_score"].sum() > 0:
            bins = pd.cut(df["match_score"], bins=[0, 49, 64, 79, 100], labels=["<50", "50-64", "65-79", "80-100"])
            chart_data = bins.value_counts().sort_index()
            st.bar_chart(chart_data, color="#6366f1")
        else:
            st.caption("No scored jobs yet.")

    with col2:
        st.markdown('<div class="section-header">🏢 Top Companies</div>', unsafe_allow_html=True)
        if "company" in df.columns:
            top_co = df["company"].value_counts().head(8)
            st.bar_chart(top_co, color="#10b981")

    # ── Recent detections table ──────────────────────────────────
    st.markdown('<div class="section-header">🕐 Recent Detections</div>', unsafe_allow_html=True)

    display_df = df.copy()

    # Posted date column — actual job posting date from source
    if "posted_date" not in display_df.columns:
        display_df["posted_date"] = display_df["detected_at"].astype(str).str[:10]
    else:
        # Use posted_date if available, fall back to detected_at
        display_df["posted_date"] = display_df["posted_date"].where(
            display_df["posted_date"].notna() & (display_df["posted_date"] != "") & (display_df["posted_date"] != "None"),
            display_df["detected_at"].astype(str).str[:10]
        )

    # Action taken column
    def _action_label(s):
        s = str(s).strip()
        if s == "Applied":      return "✅ Applied"
        if s == "Skipped":      return "🚫 Skipped"
        if s == "Interviewing": return "🎯 Interview"
        if s == "Rejected":     return "❌ Rejected"
        if s == "Offer":        return "💎 Offer"
        return "⏳ Pending"

    display_df["action"] = display_df["status"].apply(_action_label)
    display_df["detected_at"] = display_df["detected_at"].astype(str).str[:16].str.replace("T", " ")

    cols = ["detected_at", "company", "job_title", "match_score", "verdict",
            "posted_date", "action", "job_url"]
    cols = [c for c in cols if c in display_df.columns]

    st.dataframe(
        display_df[cols].head(30),
        use_container_width=True,
        hide_index=True,
        column_config={
            "detected_at":  st.column_config.TextColumn("Detected"),
            "company":      st.column_config.TextColumn("Company"),
            "job_title":    st.column_config.TextColumn("Role"),
            "match_score":  st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "verdict":      st.column_config.TextColumn("Verdict"),
            "posted_date":  st.column_config.TextColumn("Posted"),
            "action":       st.column_config.TextColumn("Action"),
            "job_url":      st.column_config.LinkColumn("Link", display_text="Apply →"),
        },
    )
