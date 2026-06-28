"""Configuration and settings management."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Paths
DB_PATH: str = os.getenv("DB_PATH", str(DATA_DIR / "applications.db"))
RESUME_PATH: str = os.getenv("RESUME_PATH", str(DATA_DIR / "resume.txt"))

# Applicant info
APPLICANT_NAME: str = os.getenv("APPLICANT_NAME", "")
APPLICANT_EMAIL: str = os.getenv("APPLICANT_EMAIL", "")
APPLICANT_PHONE: str = os.getenv("APPLICANT_PHONE", "")

# Search defaults
DEFAULT_LOCATION: str = os.getenv("DEFAULT_LOCATION", "Minneapolis, MN")

# Target job keywords for chemistry/NMR roles
TARGET_KEYWORDS = [
    "organic chemistry", "organic synthesis", "NMR", "nuclear magnetic resonance",
    "analytical chemistry", "peptide synthesis", "HPLC", "mass spectrometry",
    "structural biology", "spectroscopy", "chromatography", "laboratory",
    "research scientist", "chemist", "chemical analysis", "solution NMR",
    "solid-state NMR", "protein NMR", "small molecule", "medicinal chemistry",
    "process chemistry", "GC-MS", "LC-MS", "titration", "quantitative analysis",
]
