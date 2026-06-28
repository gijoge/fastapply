"""SQLite database layer using SQLAlchemy."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text,
    create_engine, desc
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from fastapply.config import DB_PATH
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


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    engine = init_db()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


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
        record.status = status
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
