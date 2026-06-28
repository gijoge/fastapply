"""AI-powered cover letter generator."""

from openai import OpenAI

from fastapply.config import (
    OPENAI_API_KEY, OPENAI_MODEL,
    APPLICANT_NAME, APPLICANT_EMAIL, APPLICANT_PHONE,
    RESUME_PATH,
)
from fastapply.ats_scorer import load_resume


SYSTEM_PROMPT = """
You are an expert career coach specializing in chemistry and life sciences.
You write concise, compelling cover letters that:
- Open with a specific hook referencing the company or role
- Highlight relevant technical skills (NMR, organic synthesis, analytical chemistry)
- Use concrete achievements with numbers where possible
- Close with a confident, specific call to action
- Are 3–4 paragraphs, under 350 words
- Sound human and natural, not AI-generated
Do NOT use generic phrases like 'I am writing to express my interest'.
"""


def generate_cover_letter(
    job_description: str,
    company: str,
    title: str,
    hiring_manager: str = "Hiring Manager",
    extra_context: str = "",
) -> str:
    """
    Generate a tailored cover letter.

    Args:
        job_description: Full JD text
        company: Company name
        title: Job title
        hiring_manager: Name of hiring manager (or 'Hiring Manager')
        extra_context: Any extra notes (e.g., referral, specific project)

    Returns:
        Cover letter as a formatted string
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")

    resume = load_resume()
    client = OpenAI(api_key=OPENAI_API_KEY)

    user_prompt = f"""
Applicant: {APPLICANT_NAME}
Email: {APPLICANT_EMAIL}
Phone: {APPLICANT_PHONE}

Resume:
{resume}

Job Title: {title}
Company: {company}
Hiring Manager: {hiring_manager}

Job Description:
{job_description}

Extra context from applicant:
{extra_context or 'None'}

Please write a tailored cover letter for this position.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=600,
    )

    return response.choices[0].message.content.strip()


def generate_followup_email(
    company: str,
    title: str,
    applied_date: str,
    contact_name: str = "Hiring Manager",
) -> str:
    """Generate a follow-up email for an application."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
Write a brief, professional follow-up email.
Applicant: {APPLICANT_NAME}
Applied for: {title} at {company}
Application date: {applied_date}
Recipient: {contact_name}

The email should:
- Be 3-4 sentences
- Reiterate enthusiasm for the role
- Ask about timeline
- Be polite, not pushy
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()
