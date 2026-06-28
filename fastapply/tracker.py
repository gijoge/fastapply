"""Application tracker — high-level interface over the DB layer."""

from datetime import date
from typing import List, Optional

from fastapply.db import (
    add_application, list_applications, update_status, get_stats, init_db
)
from fastapply.models import Application, ApplicationStatus


def create_application(
    company: str,
    title: str,
    url: str = "",
    status: str = "saved",
    notes: str = "",
    cover_letter: str = "",
    ats_score: Optional[float] = None,
) -> int:
    """Create and save a new application. Returns its DB id."""
    init_db()
    app = Application(
        company=company,
        title=title,
        url=url,
        status=ApplicationStatus(status),
        applied_date=date.today() if status == "applied" else None,
        notes=notes,
        cover_letter=cover_letter,
        ats_score=ats_score,
    )
    return add_application(app)


def get_all_applications(status: Optional[str] = None) -> list:
    """Return all applications, optionally filtered by status."""
    return list_applications(status=status)


def mark_applied(app_id: int, notes: str = "") -> bool:
    """Mark application as applied."""
    return update_status(app_id, ApplicationStatus.APPLIED.value, notes)


def mark_interview(app_id: int, notes: str = "") -> bool:
    """Mark application as in interview stage."""
    return update_status(app_id, ApplicationStatus.INTERVIEW.value, notes)


def mark_rejected(app_id: int, notes: str = "") -> bool:
    """Mark application as rejected."""
    return update_status(app_id, ApplicationStatus.REJECTED.value, notes)


def get_summary_stats() -> dict:
    """Return summary statistics for the dashboard."""
    return get_stats()
