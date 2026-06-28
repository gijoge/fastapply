# FastApply 🚀

AI-powered job application automation for chemistry and NMR roles in the Twin Cities (Minneapolis-St. Paul).

## Features

- 🔍 **Job Discovery** — Scrapes and filters job listings from multiple sources
- 📝 **Cover Letter Generator** — Tailors cover letters to each job description using AI
- 📊 **Application Tracker** — SQLite database to track all your applications
- 🤖 **ATS Optimizer** — Scores your resume against job descriptions for keyword match
- 📧 **Email Templates** — Follow-up email generator for after applications
- 📋 **Resume Tailor** — Suggests resume bullet point edits per job posting

## Project Structure

```
fastapply/
├── fastapply/
│   ├── __init__.py
│   ├── config.py            # Settings and configuration
│   ├── models.py            # Data models (Application, Job, etc.)
│   ├── db.py                # SQLite database layer
│   ├── scraper.py           # Job listing scraper
│   ├── ats_scorer.py        # ATS keyword scoring
│   ├── cover_letter.py      # Cover letter generator
│   ├── resume_tailor.py     # Resume tailoring suggestions
│   └── tracker.py           # Application status tracker
├── cli.py                   # Command-line interface
├── dashboard.py             # Optional: Streamlit dashboard
├── data/
│   ├── resume.txt           # Paste your plain-text resume here
│   └── applications.db      # Auto-created SQLite database
├── tests/
│   ├── test_ats_scorer.py
│   └── test_cover_letter.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/gijoge/fastapply.git
cd fastapply
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your OpenAI API key and preferences
```

### 3. Add Your Resume

Paste your resume as plain text into `data/resume.txt`.

### 4. Run

```bash
# Score a job description against your resume
python cli.py score --jd "path/to/job_description.txt"

# Generate a cover letter
python cli.py cover-letter --jd "path/to/job_description.txt" --company "Medtronic" --title "Research Scientist"

# Add an application to the tracker
python cli.py apply --company "3M" --title "Analytical Chemist" --url "https://jobs.3m.com/..."

# View all tracked applications
python cli.py list

# Launch the Streamlit dashboard
streamlit run dashboard.py
```

## ATS Scoring

FastApply compares your resume against a job description using TF-IDF keyword extraction and reports:
- Overall match score (0–100%)
- Missing high-priority keywords
- Suggested resume bullet edits to close the gap

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for AI features | required |
| `OPENAI_MODEL` | Model to use | `gpt-4o-mini` |
| `DEFAULT_LOCATION` | Job search location | `Minneapolis, MN` |
| `DB_PATH` | Path to SQLite database | `data/applications.db` |
| `RESUME_PATH` | Path to plain-text resume | `data/resume.txt` |

## Target Job Categories

FastApply is tuned for roles in:
- Organic Chemistry / Synthesis
- NMR Spectroscopy
- Analytical Chemistry
- Peptide Chemistry
- Structural Biology
- Laboratory Research Scientist

## License

MIT
