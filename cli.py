"""FastApply CLI — command-line interface."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from fastapply.ats_scorer import score_application
from fastapply.cover_letter import generate_cover_letter, generate_followup_email
from fastapply.resume_tailor import suggest_resume_edits
from fastapply.tracker import (
    create_application, get_all_applications, mark_applied,
    mark_interview, mark_rejected, get_summary_stats,
)
from fastapply.scraper import search_jobs
from fastapply.db import init_db

console = Console()


@click.group()
def cli():
    """FastApply — AI-powered job application automation."""
    init_db()


# ── ATS Scoring ──────────────────────────────────────────────────────────────

@cli.command()
@click.option("--jd", required=True, help="Path to job description text file")
@click.option("--title", default="", help="Job title")
@click.option("--company", default="", help="Company name")
def score(jd: str, title: str, company: str):
    """Score your resume against a job description."""
    jd_text = Path(jd).read_text(encoding="utf-8")
    with console.status("Analyzing..."):
        result = score_application(jd_text, job_title=title, company=company)

    console.print(Panel(
        f"[bold green]ATS Score: {result.score:.1f}%[/bold green]",
        title=f"{title} @ {company}" if title else "ATS Score",
        border_style="green" if result.score >= 60 else "yellow",
    ))

    if result.matched_keywords:
        console.print("\n[bold]✓ Matched Keywords:[/bold]")
        console.print(", ".join(result.matched_keywords[:12]))

    if result.missing_keywords:
        console.print("\n[bold red]✗ Missing Keywords:[/bold red]")
        console.print(", ".join(result.missing_keywords[:10]))

    if result.suggestions:
        console.print("\n[bold yellow]💡 Suggestions:[/bold yellow]")
        for s in result.suggestions:
            console.print(f"  • {s}")


# ── Cover Letter ─────────────────────────────────────────────────────────────

@cli.command(name="cover-letter")
@click.option("--jd", required=True, help="Path to job description text file")
@click.option("--company", required=True, help="Company name")
@click.option("--title", required=True, help="Job title")
@click.option("--manager", default="Hiring Manager", help="Hiring manager name")
@click.option("--context", default="", help="Extra context (referral, project, etc.)")
@click.option("--save", is_flag=True, help="Save to a .txt file")
def cover_letter(jd: str, company: str, title: str, manager: str, context: str, save: bool):
    """Generate a tailored cover letter."""
    jd_text = Path(jd).read_text(encoding="utf-8")
    with console.status("Generating cover letter..."):
        letter = generate_cover_letter(jd_text, company, title, manager, context)

    console.print(Panel(letter, title=f"Cover Letter: {title} @ {company}", border_style="blue"))

    if save:
        out_path = f"cover_{company.replace(' ', '_')}_{title.replace(' ', '_')}.txt"
        Path(out_path).write_text(letter, encoding="utf-8")
        console.print(f"[green]Saved to {out_path}[/green]")


# ── Resume Tailor ─────────────────────────────────────────────────────────────

@cli.command(name="tailor")
@click.option("--jd", required=True, help="Path to job description text file")
@click.option("--company", default="", help="Company name")
@click.option("--title", default="", help="Job title")
def tailor(jd: str, company: str, title: str):
    """Get AI suggestions to tailor your resume for a job."""
    jd_text = Path(jd).read_text(encoding="utf-8")
    with console.status("Generating resume suggestions..."):
        suggestions = suggest_resume_edits(jd_text, company, title)

    console.print(Panel(suggestions, title="Resume Tailoring Suggestions", border_style="magenta"))


# ── Application Tracker ───────────────────────────────────────────────────────

@cli.command(name="apply")
@click.option("--company", required=True)
@click.option("--title", required=True)
@click.option("--url", default="")
@click.option("--notes", default="")
def apply(company: str, title: str, url: str, notes: str):
    """Add an application to your tracker."""
    app_id = create_application(company, title, url=url, status="applied", notes=notes)
    console.print(f"[green]✓ Application #{app_id} added: {title} @ {company}[/green]")


@cli.command(name="save")
@click.option("--company", required=True)
@click.option("--title", required=True)
@click.option("--url", default="")
def save_job(company: str, title: str, url: str):
    """Save a job to apply later."""
    app_id = create_application(company, title, url=url, status="saved")
    console.print(f"[blue]✓ Saved #{app_id}: {title} @ {company}[/blue]")


@cli.command(name="list")
@click.option("--status", default=None, help="Filter by status (saved/applied/interview/etc.)")
def list_apps(status: Optional[str]):
    """List all tracked applications."""
    apps = get_all_applications(status=status)

    if not apps:
        console.print("[yellow]No applications found.[/yellow]")
        return

    table = Table(title="Applications", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Company", style="bold")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("ATS%", justify="right")
    table.add_column("Notes", max_width=30)

    status_colors = {
        "saved": "blue", "applied": "green", "phone_screen": "cyan",
        "interview": "yellow", "offer": "bold green", "rejected": "red",
    }

    for app in apps:
        color = status_colors.get(app.status, "white")
        table.add_row(
            str(app.id),
            app.company,
            app.title,
            f"[{color}]{app.status}[/{color}]",
            f"{app.ats_score:.0f}" if app.ats_score else "—",
            (app.notes[:40] + "...") if app.notes and len(app.notes) > 40 else (app.notes or "—"),
        )

    console.print(table)


@cli.command(name="stats")
def stats():
    """Show application pipeline statistics."""
    s = get_summary_stats()
    console.print(Panel(
        f"[bold]Total:[/bold] {s.get('total', 0)}\n"
        f"[blue]Saved:[/blue] {s.get('saved', 0)}  "
        f"[green]Applied:[/green] {s.get('applied', 0)}  "
        f"[yellow]Interview:[/yellow] {s.get('interview', 0)}  "
        f"[bold green]Offer:[/bold green] {s.get('offer', 0)}  "
        f"[red]Rejected:[/red] {s.get('rejected', 0)}",
        title="Application Pipeline",
        border_style="cyan",
    ))


@cli.command(name="update")
@click.argument("app_id", type=int)
@click.argument("status", type=click.Choice(
    ["saved", "applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]
))
@click.option("--notes", default="", help="Optional notes")
def update(app_id: int, status: str, notes: str):
    """Update application status."""
    from fastapply.db import update_status
    ok = update_status(app_id, status, notes)
    if ok:
        console.print(f"[green]✓ Application #{app_id} → {status}[/green]")
    else:
        console.print(f"[red]Application #{app_id} not found.[/red]")


# ── Job Search ────────────────────────────────────────────────────────────────

@cli.command(name="search")
@click.argument("query")
@click.option("--location", default="Minneapolis, MN")
@click.option("--max", "max_results", default=15, type=int)
def search(query: str, location: str, max_results: int):
    """Search for job listings."""
    with console.status(f"Searching for '{query}' in {location}..."):
        jobs = search_jobs(query, location, max_results=max_results)

    if not jobs:
        console.print("[yellow]No jobs found.[/yellow]")
        return

    table = Table(title=f"Results: {query} in {location}", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Source")
    table.add_column("URL", max_width=40)

    for i, job in enumerate(jobs, 1):
        table.add_row(
            str(i), job.title, job.company, job.location, job.source,
            job.url[:40] + "..." if len(job.url) > 40 else job.url,
        )

    console.print(table)


# ── Follow-Up Email ───────────────────────────────────────────────────────────

@cli.command(name="followup")
@click.option("--company", required=True)
@click.option("--title", required=True)
@click.option("--date", "applied_date", required=True, help="Date applied (YYYY-MM-DD)")
@click.option("--contact", default="Hiring Manager")
def followup(company: str, title: str, applied_date: str, contact: str):
    """Generate a follow-up email."""
    with console.status("Generating follow-up..."):
        email = generate_followup_email(company, title, applied_date, contact)
    console.print(Panel(email, title=f"Follow-up: {title} @ {company}", border_style="cyan"))


if __name__ == "__main__":
    cli()
