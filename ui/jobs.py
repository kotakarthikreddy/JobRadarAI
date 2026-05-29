"""Simple jobs list — title, company, location, link. No CV/cover letter."""
import streamlit as st
import pandas as pd

from config.candidate import KEYWORD_FILTER
from db.storage import init_db, get_ml_jobs, update_job_status


def _is_ml_title(title: str) -> bool:
    t = (title or "").lower()
    return any(kw.lower() in t for kw in KEYWORD_FILTER)


def show_jobs():
    st.title("ML / AI Jobs")
    st.caption("H1B-verified sponsors only. Click Apply to open the posting.")

    conn = init_db()
    jobs = get_ml_jobs(conn)
    conn.close()

    if not jobs:
        st.warning("No ML/AI jobs yet. Click **Scan Now** in the sidebar.")
        return

    df = pd.DataFrame(jobs)

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        search = st.text_input("Search", placeholder="company or title...")
    with c2:
        show_all = st.checkbox("Show all scores", value=True)
    with c3:
        remote_only = st.checkbox("Remote only", value=False)

    if search:
        mask = (
            df["job_title"].str.contains(search, case=False, na=False)
            | df["company"].str.contains(search, case=False, na=False)
            | df["location"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if not show_all and "match_score" in df.columns:
        df = df[df["match_score"] >= 60]

    if remote_only:
        df = df[df["location"].str.contains("remote", case=False, na=False)]

    df = df.sort_values(["detected_at", "match_score"], ascending=[False, False])

    st.write(f"**{len(df)}** jobs")
    st.divider()

    display = df[
        ["job_title", "company", "location", "match_score", "h1b_sponsor", "job_url", "detected_at", "job_id", "status"]
    ].copy()
    display["detected_at"] = display["detected_at"].astype(str).str[:10]

    st.dataframe(
        display.rename(columns={
            "job_title": "Title",
            "company": "Company",
            "location": "Location",
            "match_score": "Score",
            "h1b_sponsor": "H1B",
            "job_url": "Apply",
            "detected_at": "Found",
            "status": "Status",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Apply": st.column_config.LinkColumn("Apply", display_text="Open"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
        },
    )

    st.subheader("Quick actions")
    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        options = {
            f"{r['job_title'][:60]} @ {r['company']}": r["job_id"]
            for _, r in df.head(30).iterrows()
        }
        pick = st.selectbox("Select a job", list(options.keys()) if options else ["—"])
    with ac2:
        if st.button("Mark Applied", use_container_width=True) and options:
            conn2 = init_db()
            update_job_status(conn2, options[pick], "Applied")
            conn2.close()
            st.success("Marked applied")
            st.rerun()
    with ac3:
        if st.button("Skip", use_container_width=True) and options:
            conn2 = init_db()
            update_job_status(conn2, options[pick], "Skipped")
            conn2.close()
            st.rerun()
