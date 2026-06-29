"""SQLite database layer using SQLAlchemy."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    desc,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from fastapply.config import DB_PATH as DEFAULT_DB_PATH, DEFAULT_LOCATION, TARGET_KEYWORDS
from fastapply.models import Application, ApplicationStatus, Job
from fastapply.scraper import search_jobs


class Base(DeclarativeBase):
    pass


class ApplicationRecord(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(Text, default="")
    status = Column(String(50), default="saved")
    applied_date = Column(Date, nullable=True)
    notes = Column(Text, default="")
    cover_letter = Column(Text, default="")
    ats_score = Column(Float, nullable=True)
    contact_name = Column(String(255), default="")
    contact_email = Column(String(255), default="")
    next_action = Column(Text, default="")
    next_action_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DiscoveredJobRecord(Base):
    __tablename__ = "discovered_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, default="")
    external_id = Column(String(255), default="")
    query = Column(String(255), default="")
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    url = Column(Text, default="")
    description = Column(Text, default="")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    remote = Column(Boolean, default=False)
    posted_date = Column(Date, nullable=True)
    fingerprint = Column(String(600), nullable=False, unique=True, index=True)
    status = Column(String(50), default="new")  # new, seen, dismissed, applied
    application_id = Column(Integer, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.now)
    last_seen_at = Column(DateTime, default=datetime.now)
    last_scraped_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DiscoveryRunRecord(Base):
    __tablename__ = "discovery_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(Date, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running, success, failed
    location = Column(String(255), default="")
    sources = Column(Text, default="")
    queries = Column(Text, default="")
    inserted_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    seen_count = Column(Integer, default=0)
    error_message = Column(Text, default="")


_engine: Optional[Engine] = None
_engine_path: Optional[str] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def _current_db_path() -> str:
    """Return the active database path, allowing tests to override via env."""
    return os.getenv("DB_PATH", DEFAULT_DB_PATH)


def _build_engine(db_path: str) -> Engine:
    """Create a SQLite engine for a filesystem or shared in-memory database."""
    if db_path == ":memory:":
        return create_engine(
            "sqlite://",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    db_file = Path(db_path).expanduser()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_file.as_posix()}", echo=False)


def get_engine() -> Engine:
    """Return a cached engine for the active DB path."""
    global _engine, _engine_path, _SessionLocal

    db_path = _current_db_path()
    if _engine is None or _engine_path != db_path:
        _engine = _build_engine(db_path)
        _engine_path = db_path
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

    return _engine


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    init_db()
    if _SessionLocal is None:
        raise RuntimeError("Database session factory was not initialized")
    return _SessionLocal()


def add_application(app: Application) -> int:
    """Insert a new application, return its ID."""
    with get_session() as session:
        record = ApplicationRecord(
            company=app.company,
            title=app.title,
            url=app.url,
            status=app.status.value,
            applied_date=app.applied_date,
            notes=app.notes,
            cover_letter=app.cover_letter,
            ats_score=app.ats_score,
            contact_name=app.contact_name,
            contact_email=app.contact_email,
            next_action=app.next_action,
            next_action_date=app.next_action_date,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


def list_applications(
    status: Optional[str] = None,
    limit: int = 50
) -> List[ApplicationRecord]:
    """Return applications, optionally filtered by status."""
    with get_session() as session:
        q = session.query(ApplicationRecord).order_by(desc(ApplicationRecord.created_at))
        if status:
            q = q.filter(ApplicationRecord.status == status)
        return q.limit(limit).all()


def update_status(app_id: int, status: str, notes: str = "") -> bool:
    """Update the status of an application."""
    with get_session() as session:
        record = session.get(ApplicationRecord, app_id)
        if not record:
            return False

        new_status = ApplicationStatus(status)
        record.status = new_status.value
        if new_status == ApplicationStatus.APPLIED and record.applied_date is None:
            record.applied_date = date.today()

        if notes:
            record.notes = f"{record.notes}\n{notes}".strip()
        record.updated_at = datetime.now()
        session.commit()
        return True


def get_stats() -> dict:
    """Return summary statistics for applications and discovered jobs."""
    with get_session() as session:
        total = session.query(ApplicationRecord).count()
        stats = {"total": total}
        for s in ApplicationStatus:
            stats[s.value] = session.query(ApplicationRecord).filter(
                ApplicationRecord.status == s.value
            ).count()

        stats["discovered_jobs_total"] = session.query(DiscoveredJobRecord).count()
        stats["discovered_jobs_new"] = session.query(DiscoveredJobRecord).filter(
            DiscoveredJobRecord.status == "new"
        ).count()
        stats["discovered_jobs_applied"] = session.query(DiscoveredJobRecord).filter(
            DiscoveredJobRecord.status == "applied"
        ).count()
        return stats


def _job_fingerprint(job: Job) -> str:
    external_id = (job.external_id or "").strip().lower()
    if external_id:
        return f"{job.source.strip().lower()}::{external_id}"

    return "::".join([
        job.source.strip().lower(),
        job.company.strip().lower(),
        job.title.strip().lower(),
        job.location.strip().lower(),
        job.url.strip().lower(),
    ])


def upsert_discovered_jobs(jobs: List[Job]) -> Dict[str, int]:
    """
    Insert or update discovered jobs.
    Returns counts for inserted, updated, and seen.
    """
    inserted = 0
    updated = 0
    seen = 0
    now = datetime.now()

    with get_session() as session:
        for job in jobs:
            fingerprint = _job_fingerprint(job)
            record = session.query(DiscoveredJobRecord).filter(
                DiscoveredJobRecord.fingerprint == fingerprint
            ).one_or_none()

            if record is None:
                record = DiscoveredJobRecord(
                    source=job.source,
                    external_id=job.external_id,
                    query=job.query,
                    company=job.company,
                    title=job.title,
                    location=job.location,
                    url=job.url,
                    description=job.description,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    remote=job.remote,
                    posted_date=job.posted_date,
                    fingerprint=fingerprint,
                    status="new",
                    first_seen_at=now,
                    last_seen_at=now,
                    last_scraped_at=now,
                )
                session.add(record)
                inserted += 1
                continue

            changed = False
            updates = {
                "query": job.query,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "url": job.url,
                "description": job.description,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "remote": job.remote,
                "posted_date": job.posted_date,
                "external_id": job.external_id,
                "source": job.source,
            }

            for field_name, new_value in updates.items():
                if getattr(record, field_name) != new_value and new_value not in (None, ""):
                    setattr(record, field_name, new_value)
                    changed = True

            record.last_seen_at = now
            record.last_scraped_at = now
            record.updated_at = now

            if record.status == "dismissed":
                pass
            elif record.status == "applied":
                pass
            else:
                record.status = "seen"

            if changed:
                updated += 1
            else:
                seen += 1

        session.commit()

    return {"inserted": inserted, "updated": updated, "seen": seen}


def list_discovered_jobs(
    status: Optional[str] = None,
    limit: int = 100
) -> List[DiscoveredJobRecord]:
    """Return discovered jobs, optionally filtered by status."""
    with get_session() as session:
        q = session.query(DiscoveredJobRecord).order_by(
            desc(DiscoveredJobRecord.last_seen_at),
            desc(DiscoveredJobRecord.created_at),
        )
        if status:
            q = q.filter(DiscoveredJobRecord.status == status)
        return q.limit(limit).all()


def mark_discovered_job_status(job_id: int, status: str) -> bool:
    """Update discovered job status."""
    with get_session() as session:
        record = session.get(DiscoveredJobRecord, job_id)
        if not record:
            return False
        record.status = status
        record.updated_at = datetime.now()
        session.commit()
        return True


def link_discovered_job_to_application(job_id: int, application_id: int) -> bool:
    """Link a discovered job to an application record."""
    with get_session() as session:
        record = session.get(DiscoveredJobRecord, job_id)
        if not record:
            return False
        record.application_id = application_id
        record.status = "applied"
        record.updated_at = datetime.now()
        session.commit()
        return True


def has_successful_discovery_run_today() -> bool:
    """Return True if a successful discovery run already exists for today."""
    with get_session() as session:
        record = session.query(DiscoveryRunRecord).filter(
            DiscoveryRunRecord.run_date == date.today(),
            DiscoveryRunRecord.status == "success",
        ).order_by(desc(DiscoveryRunRecord.started_at)).first()
        return record is not None


def create_discovery_run(location: str, sources: List[str], queries: List[str]) -> int:
    """Create a discovery run record and return its ID."""
    with get_session() as session:
        record = DiscoveryRunRecord(
            run_date=date.today(),
            started_at=datetime.now(),
            status="running",
            location=location,
            sources=",".join(sources),
            queries=" | ".join(queries),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


def finish_discovery_run(
    run_id: int,
    *,
    status: str,
    inserted_count: int = 0,
    updated_count: int = 0,
    seen_count: int = 0,
    error_message: str = "",
) -> None:
    """Finalize a discovery run record."""
    with get_session() as session:
        record = session.get(DiscoveryRunRecord, run_id)
        if not record:
            return
        record.finished_at = datetime.now()
        record.status = status
        record.inserted_count = inserted_count
        record.updated_count = updated_count
        record.seen_count = seen_count
        record.error_message = error_message
        session.commit()


def run_daily_discovery(
    location: str = DEFAULT_LOCATION,
    sources: Optional[List[str]] = None,
    queries: Optional[List[str]] = None,
    force: bool = False,
) -> Dict[str, int]:
    """
    Run discovery once per day unless force=True.
    Returns summary counts.
    """
    init_db()

    if sources is None:
        sources = ["indeed", "linkedin"]

    if queries is None:
        queries = TARGET_KEYWORDS[:]

    if not force and has_successful_discovery_run_today():
        return {
            "skipped": 1,
            "inserted": 0,
            "updated": 0,
            "seen": 0,
            "queries": len(queries),
        }

    run_id = create_discovery_run(location, sources, queries)

    inserted_total = 0
    updated_total = 0
    seen_total = 0

    try:
        for query in queries:
            jobs = search_jobs(
                query=query,
                location=location,
                sources=sources,
                max_results=20,
            )

            result = upsert_discovered_jobs(jobs)
            inserted_total += result["inserted"]
            updated_total += result["updated"]
            seen_total += result["seen"]

        finish_discovery_run(
            run_id,
            status="success",
            inserted_count=inserted_total,
            updated_count=updated_total,
            seen_count=seen_total,
        )
        return {
            "skipped": 0,
            "inserted": inserted_total,
            "updated": updated_total,
            "seen": seen_total,
            "queries": len(queries),
        }

    except Exception as e:
        finish_discovery_run(
            run_id,
            status="failed",
            inserted_count=inserted_total,
            updated_count=updated_total,
            seen_count=seen_total,
            error_message=str(e),
        )
        raise


def get_latest_discovery_run() -> Optional[DiscoveryRunRecord]:
    """Return the latest discovery run."""
    with get_session() as session:
        return session.query(DiscoveryRunRecord).order_by(
            desc(DiscoveryRunRecord.started_at)
        ).first()
