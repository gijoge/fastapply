"""Resume tailoring suggestions — generates bullet point edits per JD."""

from openai import OpenAI

from fastapply.config import OPENAI_API_KEY, OPENAI_MODEL
from fastapply.ats_scorer import load_resume


def suggest_resume_edits(
    job_description: str,
    company: str = "",
    title: str = "",
) -> str:
    """
    Suggest specific resume bullet point edits to better match a JD.

    Returns a formatted list of suggestions.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")

    resume = load_resume()
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
You are an expert resume coach specializing in chemistry and laboratory science roles.

Resume:
{resume}

Job: {title} at {company}
Job Description:
{job_description}

Provide 3-5 specific, actionable suggestions to tailor the resume for this job.
For each suggestion:
1. Quote the original bullet (if applicable)
2. Provide a rewritten version with stronger keyword alignment
3. Briefly explain why the change improves ATS and human reader match

Focus on NMR, analytical chemistry, synthesis, and lab skills relevant to this role.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=800,
    )

    return response.choices[0].message.content.strip()
