"""ui/job_feed.py — Premium job card feed page"""
import streamlit as st
import pandas as pd
from db.storage import init_db, get_all_jobs, update_job_status

def _score_class(score: int) -> str:
    if score >= 80: return "strong"
    if score >= 65: return "apply"
    if score >= 50: return "gaps"
    return "skip"

def _score_label(score: int) -> str:
    if score >= 80: return "STRONG"
    if score >= 65: return "APPLY"
    if score >= 50: return "PARTIAL"
    return "LOW"

def show_job_feed():
    st.markdown("## 🔍 Job Feed")

    conn = init_db()
    jobs = get_all_jobs(conn)
    conn.close()

    if not jobs:
        st.info("No jobs found yet. Run a scan first!")
        return

    df = pd.DataFrame(jobs)

    # ── Filters ────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([3,1,1,1])
    with fc1:
        search = st.text_input("🔍 Search", placeholder="company, title, location…", label_visibility="collapsed")
    with fc2:
        status_filter = st.selectbox("Status", ["All", "New", "Applied", "Interviewing", "Rejected"], label_visibility="collapsed")
    with fc3:
        h1b_only = st.checkbox("H1B Only", value=True)
    with fc4:
        min_score = st.slider("Min Score", 0, 100, 60, label_visibility="collapsed")

    # Apply filters
    filtered = df.copy()
    if search:
        mask = filtered.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        filtered = filtered[mask]
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if h1b_only:
        filtered = filtered[filtered["h1b_sponsor"].astype(str).str.contains("Yes|✅|Verified", case=False, na=False)]
    if "match_score" in filtered.columns:
        filtered = filtered[filtered["match_score"] >= min_score]
    filtered = filtered.sort_values("match_score", ascending=False) if "match_score" in filtered.columns else filtered

    st.caption(f"Showing {len(filtered)} jobs")
    st.markdown("---")

    # ── Job Cards ──────────────────────────────────────────────
    for _, row in filtered.head(50).iterrows():
        job_id   = str(row.get("job_id", ""))
        title    = str(row.get("job_title", "Unknown Role"))
        company  = str(row.get("company", "Unknown"))
        location = str(row.get("location", ""))
        score    = int(row.get("match_score", 0))
        verdict  = str(row.get("verdict", ""))
        status   = str(row.get("status", "New"))
        url      = str(row.get("job_url", ""))
        h1b      = str(row.get("h1b_sponsor", ""))
        salary   = str(row.get("salary_estimate", ""))
        cl       = str(row.get("cover_letter", ""))
        posted   = str(row.get("detected_at", ""))[:10]
        initial  = company[0].upper() if company else "?"
        sc       = _score_class(score)
        sl       = _score_label(score)

        is_h1b   = "Yes" in h1b or "✅" in h1b or "Verified" in h1b
        is_remote = "remote" in location.lower()

        badges = ""
        if is_h1b:   badges += '<span class="badge badge-h1b">✅ H1B</span> '
        if is_remote: badges += '<span class="badge badge-remote">🌐 Remote</span> '
        if status == "New": badges += '<span class="badge badge-new">🆕 New</span>'

        st.markdown(f"""
<div class="job-card">
  <div class="job-card-header">
    <div style="display:flex;gap:14px;align-items:flex-start;flex:1">
      <div class="company-avatar">{initial}</div>
      <div style="flex:1">
        <div style="margin-bottom:6px">{badges}</div>
        <div class="job-title">{title}</div>
        <div class="job-company">{company}</div>
        <div class="meta-row">
          <div class="meta-item">📍 {location}</div>
          {"<div class='meta-item'>💰 " + salary + "</div>" if salary and salary != "Unknown" else ""}
          <div class="meta-item">📅 {posted}</div>
        </div>
      </div>
    </div>
    <div class="score-ring {sc}">
      <div class="score-value">{score}</div>
      <div class="score-label">{sl}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # Action buttons
        ba, bb, bc, bd = st.columns([2, 2, 2, 2])
        with ba:
            if url and url != "None":
                st.link_button("🔗 Apply Now", url, use_container_width=True, type="primary")
        with bb:
            if status == "New":
                if st.button("✅ Mark Applied", key=f"app_{job_id}", use_container_width=True):
                    conn2 = init_db()
                    update_job_status(conn2, job_id, "Applied")
                    conn2.close()
                    st.rerun()
        with bc:
            if cl and cl not in ("None", ""):
                with st.expander("📄 Cover Letter"):
                    st.text_area("", cl, height=250, key=f"cl_{job_id}", label_visibility="collapsed")
        with bd:
            if st.button("🚫 Skip", key=f"skip_{job_id}", use_container_width=True):
                conn2 = init_db()
                update_job_status(conn2, job_id, "Skipped")
                conn2.close()
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
