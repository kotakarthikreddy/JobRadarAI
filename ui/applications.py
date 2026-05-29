"""ui/applications.py — Application tracker page"""
import streamlit as st
import pandas as pd
from db.storage import init_db, get_all_jobs, update_job_status

def show_applications():
    st.markdown("## 📝 Application Tracker")

    conn = init_db()
    jobs = get_all_jobs(conn)
    conn.close()

    if not jobs:
        st.info("No applications tracked yet.")
        return

    df = pd.DataFrame(jobs)
    df = df[df["status"].isin(["Applied","Interviewing","Offer","Rejected","New"])]

    # ── Pipeline summary ─────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    counts = df["status"].value_counts() if "status" in df.columns else {}
    with col1:
        st.metric("📬 New",          counts.get("New", 0))
    with col2:
        st.metric("✅ Applied",      counts.get("Applied", 0))
    with col3:
        st.metric("🎯 Interviewing", counts.get("Interviewing", 0))
    with col4:
        st.metric("💎 Offer",        counts.get("Offer", 0))

    st.markdown("---")

    # Status tabs
    tabs = st.tabs(["📬 All", "✅ Applied", "🎯 Interviewing", "💎 Offer", "❌ Rejected"])

    def render_table(filtered):
        if filtered.empty:
            st.info("Nothing here yet.")
            return
        cols = [c for c in ["company","job_title","location","match_score","applied_date","follow_up_date","job_url"] if c in filtered.columns]
        st.dataframe(
            filtered[cols],
            use_container_width=True,
            column_config={
                "job_url": st.column_config.LinkColumn("Apply Link"),
                "match_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            },
        )

    with tabs[0]: render_table(df.sort_values("match_score", ascending=False) if "match_score" in df.columns else df)
    with tabs[1]: render_table(df[df["status"] == "Applied"])
    with tabs[2]: render_table(df[df["status"] == "Interviewing"])
    with tabs[3]: render_table(df[df["status"] == "Offer"])
    with tabs[4]: render_table(df[df["status"] == "Rejected"])

    # ── Manual status update ─────────────────────────────────
    st.markdown("---")
    st.subheader("✏️ Update Status")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        job_options = {f"{r.get('job_title','?')} @ {r.get('company','?')}": r.get("job_id","") for _, r in df.iterrows()}
        selected_label = st.selectbox("Select Job", list(job_options.keys()))
    with c2:
        new_status = st.selectbox("New Status", ["Applied","Interviewing","Offer","Rejected","Skipped"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Update", type="primary"):
            job_id = job_options.get(selected_label, "")
            if job_id:
                conn2 = init_db()
                update_job_status(conn2, job_id, new_status)
                conn2.close()
                st.success(f"Updated to {new_status}!")
                st.rerun()
