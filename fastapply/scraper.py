"""Job listing discovery and provider aggregation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from fastapply.config import DEFAULT_LOCATION
from fastapply.models import Job


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class JobProvider(ABC):
    """Abstract base class for job search providers."""

    name: str = "provider"

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @abstractmethod
    def search(self, query: str, location: str, max_results: int = 20) -> List[Job]:
        """Return normalized jobs for this provider."""

    def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        timeout: int = 10,
    ) -> requests.Response:
        resp = self.session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join((value or "").split())

    def _build_job(
        self,
        *,
        title: str,
        company: str,
        location: str = "",
        url: str = "",
        description: str = "",
        remote: bool = False,
        source: str = "",
        external_id: str = "",
        query: str = "",
    ) -> Job:
        return Job(
            title=self._normalize_text(title),
            company=self._normalize_text(company),
            location=self._normalize_text(location),
            url=url.strip(),
            description=self._normalize_text(description),
            remote=remote,
            source=source or self.name,
            external_id=external_id,
            query=query,
        )


class IndeedProvider(JobProvider):
    """Indeed HTML scraper."""

    name = "indeed"

    def search(self, query: str, location: str, max_results: int = 20) -> List[Job]:
        url = "https://www.indeed.com/jobs"
        params = {"q": query, "l": location, "limit": max_results}
        jobs: List[Job] = []

        try:
            resp = self._get(url, params=params)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select("div.job_seen_beacon")[:max_results]:
                title_el = card.select_one("h2.jobTitle span")
                company_el = card.select_one("span.companyName")
                location_el = card.select_one("div.companyLocation")
                link_el = card.select_one("h2.jobTitle a")

                if not title_el or not company_el:
                    continue

                href = link_el.get("href", "") if link_el else ""
                external_id = card.get("data-jk", "")

                jobs.append(
                    self._build_job(
                        title=title_el.get_text(strip=True),
                        company=company_el.get_text(strip=True),
                        location=location_el.get_text(strip=True) if location_el else location,
                        url=f"https://www.indeed.com{href}" if href else "",
                        source="Indeed",
                        external_id=external_id,
                        query=query,
                    )
                )
        except Exception as e:
            print(f"[scraper:{self.name}] {e}")

        return jobs


class LinkedInProvider(JobProvider):
    """Public LinkedIn jobs search scraper."""

    name = "linkedin"

    def search(self, query: str, location: str, max_results: int = 20) -> List[Job]:
        url = "https://www.linkedin.com/jobs/search"
        params = {
            "keywords": query,
            "location": location,
            "f_TPR": "r604800",  # past week
        }
        jobs: List[Job] = []

        try:
            resp = self._get(url, params=params)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select("div.base-card")[:max_results]:
                title_el = card.select_one("h3.base-search-card__title")
                company_el = card.select_one("h4.base-search-card__subtitle")
                location_el = card.select_one("span.job-search-card__location")
                link_el = card.select_one("a.base-card__full-link")

                if not title_el or not company_el:
                    continue

                href = link_el.get("href", "") if link_el else ""
                parsed = urlparse(href)
                external_id = parse_qs(parsed.query).get("currentJobId", [""])[0]

                jobs.append(
                    self._build_job(
                        title=title_el.get_text(strip=True),
                        company=company_el.get_text(strip=True),
                        location=location_el.get_text(strip=True) if location_el else location,
                        url=href,
                        source="LinkedIn",
                        external_id=external_id,
                        query=query,
                    )
                )
        except Exception as e:
            print(f"[scraper:{self.name}] {e}")

        return jobs


class GreenhouseProvider(JobProvider):
    """Placeholder for Greenhouse board integrations."""

    name = "greenhouse"

    def search(self, query: str, location: str, max_results: int = 20) -> List[Job]:
        return []


class LeverProvider(JobProvider):
    """Placeholder for Lever board integrations."""

    name = "lever"

    def search(self, query: str, location: str, max_results: int = 20) -> List[Job]:
        return []


PROVIDERS: Dict[str, JobProvider] = {
    "indeed": IndeedProvider(),
    "linkedin": LinkedInProvider(),
    "greenhouse": GreenhouseProvider(),
    "lever": LeverProvider(),
}


def get_provider(name: str) -> JobProvider:
    """Return a registered provider by name."""
    key = name.strip().lower()
    if key not in PROVIDERS:
        raise ValueError(f"Unknown job provider: {name}")
    return PROVIDERS[key]


def list_providers() -> List[str]:
    """Return all registered provider names."""
    return list(PROVIDERS.keys())


def register_provider(provider: JobProvider) -> None:
    """Register a provider instance."""
    PROVIDERS[provider.name.lower()] = provider


def _iter_selected_providers(sources: Optional[Iterable[str]]) -> List[JobProvider]:
    if sources is None:
        sources = ["indeed", "linkedin"]
    return [get_provider(source) for source in sources]


def _job_key(job: Job) -> tuple:
    external_id = (job.external_id or "").strip().lower()
    if external_id:
        return (job.source.lower(), external_id)

    return (
        job.source.lower(),
        job.company.strip().lower(),
        job.title.strip().lower(),
        job.location.strip().lower(),
        job.url.strip().lower(),
    )


def search_jobs(
    query: str,
    location: str = DEFAULT_LOCATION,
    sources: Optional[List[str]] = None,
    max_results: int = 20,
) -> List[Job]:
    """Aggregate search across enabled providers."""
    results: List[Job] = []

    for provider in _iter_selected_providers(sources):
        try:
            results.extend(provider.search(query, location, max_results))
        except Exception as e:
            print(f"[scraper:{provider.name}] {e}")

    seen = set()
    unique: List[Job] = []
    for job in results:
        key = _job_key(job)
        if key not in seen:
            seen.add(key)
            unique.append(job)

    return unique
