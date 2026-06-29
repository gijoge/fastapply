"""SQLite database layer using SQLAlchemy."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text,
    create_engine, desc
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from fastapply.config import DB_PATH as DEFAULT_DB_PATH
from fastapply.models import Application, ApplicationStatus


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
    """Return summary statistics."""
    with get_session() as session:
        total = session.query(ApplicationRecord).count()
        stats = {"total": total}
        for s in ApplicationStatus:
            stats[s.value] = session.query(ApplicationRecord).filter(
                ApplicationRecord.status == s.value
            ).count()
        return stats
