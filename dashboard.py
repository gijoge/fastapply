"""Streamlit dashboard for FastApply."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from fastapply.ats_scorer import score_application
from fastapply.cover_letter import generate_cover_letter
from fastapply.db import (
    get_latest_discovery_run,
    get_stats,
    init_db,
    list_applications,
    list_discovered_jobs,
    mark_discovered_job_status,
    run_daily_discovery,
)
from fastapply.tracker import create_application


st.set_page_config(
    page_title="FastApply Dashboard",
    page_icon="🚀",
    layout="wide",
)

init_db()


def _status_options() -> list[str]:
    return ["all", "new", "seen", "dismissed", "applied"]


def _application_status_options() -> list[str]:
    return ["all", "saved", "applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]


def _safe_str(value) -> str:
    return "" if value is None else str(value)


def _render_overview():
    st.title("FastApply Overview")
    st.caption("Tracked applications and automatically discovered jobs")

    stats = get_stats()
    latest_run = get_latest_discovery_run()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Applications", stats.get("total", 0))
    col2.metric("Applied", stats.get("applied", 0))
    col3.metric("Interview", stats.get("interview", 0))
    col4.metric("Discovered", stats.get("discovered_jobs_total", 0))
    col5.metric("New Jobs", stats.get("discovered_jobs_new", 0))

    if latest_run:
        st.info(
            f"Latest discovery run: {latest_run.status} on {latest_run.run_date} "
            f"({latest_run.inserted_count} new, {latest_run.updated_count} updated, {latest_run.seen_count} unchanged)"
        )

    st.subheader("Application Funnel")
    funnel_data = pd.DataFrame({
        "Stage": ["Saved", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"],
        "Count": [
            stats.get("saved", 0),
            stats.get("applied", 0),
            stats.get("phone_screen", 0),
            stats.get("interview", 0),
            stats.get("offer", 0),
            stats.get("rejected", 0),
        ],
    })
    fig = px.funnel(funnel_data, x="Count", y="Stage", title="Application Funnel")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Applications")
    apps = list_applications(limit=15)
    if apps:
        df = pd.DataFrame([
            {
                "ID": a.id,
                "Company": a.company,
                "Title": a.title,
                "Status": a.status,
                "Applied": a.applied_date,
                "ATS %": a.ats_score,
                "URL": a.url,
            }
            for a in apps
        ])
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL"),
            },
        )
    else:
        st.info("No applications yet.")

    st.subheader("Newest Discovered Jobs")
    jobs = list_discovered_jobs(limit=15)
    if jobs:
        jobs_df = pd.DataFrame([
            {
                "ID": j.id,
                "Source": j.source,
                "Company": j.company,
                "Title": j.title,
                "Location": j.location,
                "Status": j.status,
                "Query": j.query,
                "URL": j.url,
            }
            for j in jobs
        ])
        st.dataframe(
            jobs_df,
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("Job URL"),
            },
        )
    else:
        st.info("No discovered jobs yet.")


def _render_add_application():
    st.title("Add Application")

    with st.form("add_application_form"):
        company = st.text_input("Company *")
        title = st.text_input("Job Title *")
        url = st.text_input("Job URL")
        status = st.selectbox("Status", ["saved", "applied", "phone_screen", "interview"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save Application")

    if submitted:
        if not company or not title:
            st.error("Company and Job Title are required.")
            return

        app_id = create_application(
            company=company,
            title=title,
            url=url,
            status=status,
            notes=notes,
        )
        st.success(f"Application #{app_id} saved.")


def _render_ats_scorer():
    st.title("ATS Keyword Scorer")

    col1, col2 = st.columns(2)
    with col1:
        jd_text = st.text_area("Paste Job Description", height=300)
    with col2:
        job_title = st.text_input("Job Title")
        company_name = st.text_input("Company")

    if st.button("Score Resume"):
        if not jd_text.strip():
            st.error("Please paste a job description.")
            return

        with st.spinner("Analyzing..."):
            try:
                result = score_application(jd_text, job_title, company_name)
                st.metric("ATS Match Score", f"{result.score:.1f}%")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Matched Keywords")
                    st.write(", ".join(result.matched_keywords) if result.matched_keywords else "None")
                with col_b:
                    st.subheader("Missing Keywords")
                    st.write(", ".join(result.missing_keywords) if result.missing_keywords else "None")

                if result.suggestions:
                    st.subheader("Suggestions")
                    for s in result.suggestions:
                        st.markdown(f"- {s}")
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error: {e}")


def _render_cover_letter():
    st.title("Cover Letter Generator")

    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("Company *", key="cl_company")
        title = st.text_input("Job Title *", key="cl_title")
        manager = st.text_input("Hiring Manager", "Hiring Manager")
    with col2:
        jd_text = st.text_area("Paste Job Description *", height=220)
        context = st.text_area("Extra context (optional)", height=100)

    if st.button("Generate Cover Letter"):
        if not company or not title or not jd_text.strip():
            st.error("Company, Job Title, and Job Description are required.")
            return

        with st.spinner("Generating..."):
            try:
                letter = generate_cover_letter(jd_text, company, title, manager, context)
                st.text_area("Your Cover Letter", letter, height=400)
                st.download_button(
                    "Download .txt",
                    letter,
                    file_name=f"cover_{company}_{title}.txt",
                )
            except Exception as e:
                st.error(f"Error: {e}")


def _render_all_applications():
    st.title("All Applications")

    status_filter = st.selectbox(
        "Filter by Status",
        _application_status_options(),
        index=0,
    )

    apps = list_applications(
        status=None if status_filter == "all" else status_filter,
        limit=500,
    )

    if apps:
        df = pd.DataFrame([
            {
                "ID": a.id,
                "Company": a.company,
                "Title": a.title,
                "Status": a.status,
                "Applied Date": a.applied_date,
                "ATS %": a.ats_score,
                "Notes": a.notes,
                "URL": a.url,
            }
            for a in apps
        ])
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("Application URL"),
            },
        )
    else:
        st.info("No applications match the selected filter.")


def _render_discovered_jobs():
    st.title("Discovered Jobs")
    st.caption("Jobs pulled automatically into SQLite from the discovery pipeline")

    top1, top2 = st.columns([1, 1])

    with top1:
        if st.button("Run discovery now"):
            with st.spinner("Running discovery..."):
                try:
                    result = run_daily_discovery(force=True)
                    st.success(
                        f"Discovery complete: {result.get('inserted', 0)} new, "
                        f"{result.get('updated', 0)} updated, "
                        f"{result.get('seen', 0)} unchanged."
                    )
                except Exception as e:
                    st.error(f"Discovery failed: {e}")

    with top2:
        latest_run = get_latest_discovery_run()
        if latest_run:
            st.info(
                f"Latest run: {latest_run.status} on {latest_run.run_date} "
                f"({latest_run.inserted_count} new, {latest_run.updated_count} updated)"
            )

    status_filter = st.selectbox(
        "Filter by discovered job status",
        _status_options(),
        index=0,
    )
    limit = st.slider("Rows to show", min_value=25, max_value=500, value=100, step=25)

    jobs = list_discovered_jobs(
        status=None if status_filter == "all" else status_filter,
        limit=limit,
    )

    if not jobs:
        st.warning("No discovered jobs found.")
        return

    jobs_df = pd.DataFrame([
        {
            "ID": j.id,
            "Source": j.source,
            "Company": j.company,
            "Title": j.title,
            "Location": j.location,
            "Status": j.status,
            "Query": j.query,
            "First Seen": j.first_seen_at,
            "Last Seen": j.last_seen_at,
            "URL": j.url,
        }
        for j in jobs
    ])

    st.dataframe(
        jobs_df,
        use_container_width=True,
        column_config={
            "URL": st.column_config.LinkColumn("Job URL"),
        },
    )

    st.subheader("Update Job Status")

    job_ids = [j.id for j in jobs]
    selected_job_id: Optional[int] = st.selectbox(
        "Select discovered job ID",
        options=job_ids,
        index=0 if job_ids else None,
    )
    new_status = st.selectbox(
        "New status",
        options=["new", "seen", "dismissed", "applied"],
        index=0,
    )

    if st.button("Update discovered job status"):
        if selected_job_id is None:
            st.error("No job selected.")
            return

        ok = mark_discovered_job_status(selected_job_id, new_status)
        if ok:
            st.success(f"Discovered job #{selected_job_id} updated to '{new_status}'.")
        else:
            st.error("Could not update discovered job.")


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("FastApply")
page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Discovered Jobs",
        "All Applications",
        "Add Application",
        "ATS Scorer",
        "Cover Letter",
    ],
)

if page == "Overview":
    _render_overview()
elif page == "Discovered Jobs":
    _render_discovered_jobs()
elif page == "All Applications":
    _render_all_applications()
elif page == "Add Application":
    _render_add_application()
elif page == "ATS Scorer":
    _render_ats_scorer()
elif page == "Cover Letter":
    _render_cover_letter()
