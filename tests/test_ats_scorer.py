"""Tests for ATS scorer."""

import pytest
from fastapply.ats_scorer import extract_keywords, cosine_score, find_missing_keywords


def test_extract_keywords_basic():
    text = "NMR spectroscopy organic chemistry peptide synthesis laboratory research"
    keywords = extract_keywords(text, top_n=10)
    assert len(keywords) > 0
    assert isinstance(keywords[0], str)


def test_cosine_score_identical():
    text = "organic chemist with NMR experience in Minneapolis"
    score = cosine_score(text, text)
    assert score == 100.0


def test_cosine_score_unrelated():
    resume = "NMR spectroscopy organic synthesis peptide"
    jd = "software engineer python javascript frontend"
    score = cosine_score(resume, jd)
    assert score < 30.0


def test_find_missing_keywords():
    resume = "NMR spectroscopy organic chemistry"
    jd_keywords = ["NMR", "HPLC", "peptide synthesis", "mass spectrometry"]
    missing = find_missing_keywords(resume, jd_keywords)
    assert "HPLC" in missing
    assert "mass spectrometry" in missing
    # NMR is in resume, should not be missing
    assert "NMR" not in missing
