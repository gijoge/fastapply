"""Tests for application tracker."""

import pytest
import os

# Use an in-memory test DB
os.environ["DB_PATH"] = ":memory:"

from fastapply.db import (
    ApplicationRecord,
    add_application,
    get_session,
    get_stats,
    init_db,
    list_applications,
    update_status,
)
from fastapply.models import Application, ApplicationStatus


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with get_session() as session:
        session.query(ApplicationRecord).delete()
        session.commit()


def test_add_and_list_application():
    app = Application(
        company="Medtronic",
        title="Research Scientist",
        url="https://jobs.medtronic.com/test",
        status=ApplicationStatus.APPLIED,
        notes="Applied via website",
    )
    app_id = add_application(app)
    assert app_id is not None

    apps = list_applications()
    assert len(apps) >= 1
    assert apps[0].company == "Medtronic"


def test_stats():
    app = Application(
        company="3M",
        title="Analytical Chemist",
        status=ApplicationStatus.SAVED,
    )
    add_application(app)
    stats = get_stats()
    assert stats["total"] == 1
    assert stats["saved"] == 1


def test_update_status_sets_applied_date():
    app = Application(
        company="Mayo Clinic",
        title="Research Technologist",
        status=ApplicationStatus.SAVED,
    )
    app_id = add_application(app)

    assert update_status(app_id, "applied")

    apps = list_applications()
    assert apps[0].status == ApplicationStatus.APPLIED.value
    assert apps[0].applied_date is not None
