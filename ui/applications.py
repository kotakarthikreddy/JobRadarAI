"""ui/applications.py — Application pipeline tracker"""
import streamlit as st
import pandas as pd
from db.storage import init_db, get_all_jobs, update_job_status


def show_applications():
    st.markdown('<div class="section-header">📝 Application Pipeline</div>', unsafe_allow_html=True)

    conn = init_db()
    jobs = get_all_jobs(conn)
    conn.close()

    if not jobs:
        st.info("No applications tracked yet. Apply to jobs from the Job Feed!")
        return

    df = pd.DataFrame(jobs)
    df = df[df["status"].isin(["New", "Applied", "Interviewing", "Offer", "Rejected"])]

    # ── Pipeline metrics ─────────────────────────────────────────
    counts = df["status"].value_counts()
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-icon">📬</div>
            <div class="metric-value amber">{counts.get("New", 0)}</div>
            <div class="metric-label">New</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">✅</div>
            <div class="metric-value blue">{counts.get("Applied", 0)}</div>
            <div class="metric-label">Applied</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value purple">{counts.get("Interviewing", 0)}</div>
            <div class="metric-label">Interviewing</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">💎</div>
            <div class="metric-value green">{counts.get("Offer", 0)}</div>
            <div class="metric-label">Offers</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">❌</div>
            <div class="metric-value rose">{counts.get("Rejected", 0)}</div>
            <div class="metric-label">Rejected</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs by status ───────────────────────────────────────────
    tabs = st.tabs(["📋 All", "✅ Applied", "🎯 Interviewing", "💎 Offers", "❌ Rejected"])

    def render_table(filtered_df):
        if filtered_df.empty:
            st.caption("Nothing here yet.")
            return
        display = filtered_df.copy()
        display["detected_at"] = display["detected_at"].astype(str).str[:10]
        cols = [c for c in ["company", "job_title", "location", "match_score",
                            "applied_date", "follow_up_date", "job_url"] if c in display.columns]
        st.dataframe(
            display[cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "company":        st.column_config.TextColumn("Company"),
                "job_title":      st.column_config.TextColumn("Role"),
                "location":       st.column_config.TextColumn("Location"),
                "match_score":    st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                "applied_date":   st.column_config.TextColumn("Applied"),
                "follow_up_date": st.column_config.TextColumn("Follow Up"),
                "job_url":        st.column_config.LinkColumn("Link", display_text="Open →"),
            },
        )

    with tabs[0]:
        render_table(df.sort_values("match_score", ascending=False) if "match_score" in df.columns else df)
    with tabs[1]:
        render_table(df[df["status"] == "Applied"])
    with tabs[2]:
        render_table(df[df["status"] == "Interviewing"])
    with tabs[3]:
        render_table(df[df["status"] == "Offer"])
    with tabs[4]:
        render_table(df[df["status"] == "Rejected"])

    # ── Quick status update ──────────────────────────────────────
    st.markdown('<div class="section-header">✏️ Update Status</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        options = {
            f"{r.get('job_title', '?')[:50]} @ {r.get('company', '?')}": r.get("job_id", "")
            for _, r in df.head(30).iterrows()
        }
        if options:
            selected = st.selectbox("Select job", list(options.keys()), label_visibility="collapsed")
        else:
            selected = None
    with c2:
        new_status = st.selectbox("Status", ["Applied", "Interviewing", "Offer", "Rejected", "Skipped"], label_visibility="collapsed")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Update", type="primary", use_container_width=True) and selected:
            job_id = options[selected]
            conn2 = init_db()
            update_job_status(conn2, job_id, new_status)
            conn2.close()
            st.success(f"→ {new_status}")
            st.rerun()
