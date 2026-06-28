"""Job listing scraper — fetches listings from public job boards."""

from typing import List
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

from fastapply.config import DEFAULT_LOCATION
from fastapply.models import Job


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def search_indeed(
    query: str,
    location: str = DEFAULT_LOCATION,
    max_results: int = 20,
) -> List[Job]:
    """
    Fetch job listings from Indeed (basic scraper).
    NOTE: Indeed frequently changes its HTML — update selectors as needed.
    """
    url = "https://www.indeed.com/jobs"
    params = {"q": query, "l": location, "limit": max_results}

    jobs = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for card in soup.select("div.job_seen_beacon")[:max_results]:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span.companyName")
            location_el = card.select_one("div.companyLocation")
            link_el = card.select_one("h2.jobTitle a")

            if title_el and company_el:
                jobs.append(Job(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True),
                    location=location_el.get_text(strip=True) if location_el else location,
                    url="https://www.indeed.com" + (link_el["href"] if link_el else ""),
                    source="Indeed",
                ))
    except Exception as e:
        print(f"[scraper] Indeed error: {e}")

    return jobs


def search_linkedin(
    query: str,
    location: str = DEFAULT_LOCATION,
    max_results: int = 20,
) -> List[Job]:
    """
    Fetch public LinkedIn job listings (no login required for public search).
    """
    url = "https://www.linkedin.com/jobs/search"
    params = {
        "keywords": query,
        "location": location,
        "f_TPR": "r604800",  # Past week
    }

    jobs = []
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for card in soup.select("div.base-card")[:max_results]:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")

            if title_el and company_el:
                jobs.append(Job(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True),
                    location=location_el.get_text(strip=True) if location_el else location,
                    url=link_el["href"] if link_el else "",
                    source="LinkedIn",
                ))
    except Exception as e:
        print(f"[scraper] LinkedIn error: {e}")

    return jobs


def search_jobs(
    query: str,
    location: str = DEFAULT_LOCATION,
    sources: List[str] = None,
    max_results: int = 20,
) -> List[Job]:
    """Aggregate search across all enabled sources."""
    if sources is None:
        sources = ["indeed", "linkedin"]

    results = []
    if "indeed" in sources:
        results.extend(search_indeed(query, location, max_results))
    if "linkedin" in sources:
        results.extend(search_linkedin(query, location, max_results))

    # Deduplicate by title+company
    seen = set()
    unique = []
    for job in results:
        key = (job.title.lower(), job.company.lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)

    return unique
