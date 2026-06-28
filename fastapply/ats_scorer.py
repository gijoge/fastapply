"""ATS keyword scoring — compares resume against a job description."""

import re
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from fastapply.config import RESUME_PATH, TARGET_KEYWORDS
from fastapply.models import ATSResult


def load_resume() -> str:
    """Load resume text from disk."""
    try:
        with open(RESUME_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Resume not found at {RESUME_PATH}. "
            "Please paste your plain-text resume into data/resume.txt"
        )


def extract_keywords(text: str, top_n: int = 30) -> List[str]:
    """Extract top TF-IDF keywords from text."""
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=200,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        top_indices = scores.argsort()[-top_n:][::-1]
        return [feature_names[i] for i in top_indices if scores[i] > 0]
    except ValueError:
        return []


def cosine_score(resume: str, job_description: str) -> float:
    """Compute cosine similarity between resume and JD."""
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform([resume, job_description])
        sim = cosine_similarity(matrix[0], matrix[1])[0][0]
        return round(float(sim) * 100, 1)
    except ValueError:
        return 0.0


def find_missing_keywords(resume: str, jd_keywords: List[str]) -> List[str]:
    """Return JD keywords not found in the resume."""
    resume_lower = resume.lower()
    return [
        kw for kw in jd_keywords
        if kw.lower() not in resume_lower
    ]


def score_application(
    job_description: str,
    job_title: str = "",
    company: str = "",
) -> ATSResult:
    """Full ATS scoring pipeline."""
    resume = load_resume()
    score = cosine_score(resume, job_description)

    jd_keywords = extract_keywords(job_description, top_n=40)
    resume_keywords = extract_keywords(resume, top_n=40)

    # Also check domain-specific target keywords
    domain_missing = [
        kw for kw in TARGET_KEYWORDS
        if kw.lower() in job_description.lower()
        and kw.lower() not in resume.lower()
    ]

    missing = list(dict.fromkeys(domain_missing + find_missing_keywords(resume, jd_keywords)))
    matched = [kw for kw in jd_keywords if kw.lower() in resume.lower()]

    suggestions = [
        f"Add '{kw}' to your skills or experience section"
        for kw in missing[:8]
    ]

    return ATSResult(
        score=score,
        matched_keywords=matched[:15],
        missing_keywords=missing[:15],
        suggestions=suggestions,
        job_title=job_title,
        company=company,
    )
