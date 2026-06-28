"""Optional Streamlit dashboard for FastApply."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from fastapply.db import init_db, list_applications, get_stats
from fastapply.tracker import create_application, mark_applied, mark_interview, mark_rejected
from fastapply.ats_scorer import score_application
from fastapply.cover_letter import generate_cover_letter

st.set_page_config(
    page_title="FastApply Dashboard",
    page_icon="🚀",
    layout="wide",
)

init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🚀 FastApply")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "➕ Add Application", "🔍 ATS Scorer", "✍️ Cover Letter", "📋 All Applications"],
)

# ── Dashboard ─────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.title("Application Pipeline")
    stats = get_stats()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total", stats.get("total", 0))
    col2.metric("Applied", stats.get("applied", 0))
    col3.metric("Interview", stats.get("interview", 0))
    col4.metric("Offer", stats.get("offer", 0))
    col5.metric("Rejected", stats.get("rejected", 0))

    # Pipeline funnel chart
    funnel_data = pd.DataFrame({
        "Stage": ["Saved", "Applied", "Phone Screen", "Interview", "Offer"],
        "Count": [
            stats.get("saved", 0), stats.get("applied", 0),
            stats.get("phone_screen", 0), stats.get("interview", 0),
            stats.get("offer", 0),
        ],
    })
    fig = px.funnel(funnel_data, x="Count", y="Stage", title="Application Funnel")
    st.plotly_chart(fig, use_container_width=True)

    # Recent applications table
    st.subheader("Recent Applications")
    apps = list_applications(limit=20)
    if apps:
        df = pd.DataFrame([
            {
                "ID": a.id, "Company": a.company, "Title": a.title,
                "Status": a.status, "ATS %": a.ats_score,
                "Applied": a.applied_date, "Notes": a.notes,
            }
            for a in apps
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No applications yet. Add your first one!")

# ── Add Application ───────────────────────────────────────────────────────────
elif page == "➕ Add Application":
    st.title("Add Application")
    with st.form("add_app"):
        company = st.text_input("Company *")
        title = st.text_input("Job Title *")
        url = st.text_input("Job URL")
        status = st.selectbox("Status", ["saved", "applied", "phone_screen", "interview"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save Application")

    if submitted and company and title:
        app_id = create_application(company, title, url=url, status=status, notes=notes)
        st.success(f"✅ Application #{app_id} saved!")

# ── ATS Scorer ────────────────────────────────────────────────────────────────
elif page == "🔍 ATS Scorer":
    st.title("ATS Keyword Scorer")
    col1, col2 = st.columns(2)
    with col1:
        jd_text = st.text_area("Paste Job Description", height=300)
    with col2:
        job_title = st.text_input("Job Title")
        company_name = st.text_input("Company")

    if st.button("Score Resume") and jd_text:
        with st.spinner("Analyzing..."):
            try:
                result = score_application(jd_text, job_title, company_name)
                st.metric("ATS Match Score", f"{result.score:.1f}%")
                color = "green" if result.score >= 60 else "orange" if result.score >= 40 else "red"
                st.markdown(f"<h2 style='color:{color}'>{result.score:.1f}%</h2>", unsafe_allow_html=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("✅ Matched Keywords")
                    st.write(", ".join(result.matched_keywords))
                with col_b:
                    st.subheader("❌ Missing Keywords")
                    st.write(", ".join(result.missing_keywords))

                if result.suggestions:
                    st.subheader("💡 Suggestions")
                    for s in result.suggestions:
                        st.markdown(f"- {s}")
            except FileNotFoundError as e:
                st.error(str(e))

# ── Cover Letter ──────────────────────────────────────────────────────────────
elif page == "✍️ Cover Letter":
    st.title("Cover Letter Generator")
    col1, col2 = st.columns(2)
    with col1:
        cl_company = st.text_input("Company *")
        cl_title = st.text_input("Job Title *")
        cl_manager = st.text_input("Hiring Manager", "Hiring Manager")
    with col2:
        cl_jd = st.text_area("Paste Job Description *", height=200)
        cl_context = st.text_area("Extra context (optional)", height=80)

    if st.button("Generate Cover Letter") and cl_company and cl_title and cl_jd:
        with st.spinner("Generating..."):
            try:
                letter = generate_cover_letter(cl_jd, cl_company, cl_title, cl_manager, cl_context)
                st.text_area("Your Cover Letter", letter, height=400)
                st.download_button(
                    "⬇️ Download .txt",
                    letter,
                    file_name=f"cover_{cl_company}_{cl_title}.txt",
                )
            except Exception as e:
                st.error(f"Error: {e}")

# ── All Applications ──────────────────────────────────────────────────────────
elif page == "📋 All Applications":
    st.title("All Applications")
    status_filter = st.selectbox(
        "Filter by Status",
        ["all", "saved", "applied", "phone_screen", "interview", "offer", "rejected"],
    )
    apps = list_applications(status=None if status_filter == "all" else status_filter, limit=100)
    if apps:
        df = pd.DataFrame([
            {
                "ID": a.id, "Company": a.company, "Title": a.title,
                "Status": a.status, "ATS %": a.ats_score,
                "Applied Date": a.applied_date, "Notes": a.notes,
                "URL": a.url,
            }
            for a in apps
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No applications match the selected filter.")
