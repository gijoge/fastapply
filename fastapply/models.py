"""Data models for FastApply."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class Job:
    """A normalized job listing from any provider."""
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    remote: bool = False
    posted_date: Optional[date] = None
    source: str = ""          # e.g., "Indeed", "LinkedIn", "Greenhouse", "Lever"
    external_id: str = ""     # provider-specific stable ID when available
    query: str = ""           # search query that produced this listing


@dataclass
class Application:
    """A tracked job application."""
    id: Optional[int] = None
    company: str = ""
    title: str = ""
    url: str = ""
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_date: Optional[date] = None
    notes: str = ""
    cover_letter: str = ""
    ats_score: Optional[float] = None
    contact_name: str = ""
    contact_email: str = ""
    next_action: str = ""
    next_action_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ATSResult:
    """Result of an ATS scoring run."""
    score: float  # 0.0 to 100.0
    matched_keywords: list
    missing_keywords: list
    suggestions: list
    job_title: str = ""
    company: str = ""
