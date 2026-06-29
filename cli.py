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
from fastapply.db import (
    init_db,
    list_discovered_jobs,
    run_daily_discovery,
    get_latest_discovery_run,
)

console = Console()


def _auto_discover_jobs() -> None:
    """Run job discovery automatically at most once per day."""
    try:
        result = run_daily_discovery()
        if result.get("skipped"):
            return

        inserted = result.get("inserted", 0)
        updated = result.get("updated", 0)
        seen = result.get("seen", 0)

        console.print(
            f"[cyan]Auto-discovery complete:[/cyan] "
            f"{inserted} new, {updated} updated, {seen} unchanged jobs."
        )
    except Exception as e:
        console.print(f"[yellow]Auto-discovery warning:[/yellow] {e}")


@click.group()
def cli():
    """FastApply — AI-powered job application automation."""
    init_db()
    _auto_discover_jobs()


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
    console.print(f"[green]Tracked application #{app_id}: {title} @ {company}[/green]")


@cli.command(name="save-job")
@click.option("--company", required=True)
@click.option("--title", required=True)
@click.option("--url", default="")
@click.option("--notes", default="")
def save_job(company: str, title: str, url: str, notes: str):
    """Save a job to your tracker without marking it applied."""
    app_id = create_application(company, title, url=url, status="saved", notes=notes)
    console.print(f"[green]Saved job #{app_id}: {title} @ {company}[/green]")


@cli.command(name="list")
@click.option("--status", default=None, help="Filter by status")
def list_cmd(status: Optional[str]):
    """List tracked applications."""
    rows = get_all_applications(status=status)
    table = Table(title="Tracked Applications")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Company", style="bold")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Applied")
    table.add_column("ATS")

    for row in rows:
        table.add_row(
            str(row.id),
            row.company,
            row.title,
            row.status,
            str(row.applied_date or ""),
            f"{row.ats_score:.1f}" if row.ats_score is not None else "",
        )

    console.print(table)


@cli.command(name="jobs")
@click.option("--status", default=None, help="Filter discovered jobs by status")
@click.option("--limit", default=50, help="Max discovered jobs to show")
def jobs_cmd(status: Optional[str], limit: int):
    """List automatically discovered jobs from SQLite."""
    rows = list_discovered_jobs(status=status, limit=limit)

    table = Table(title="Discovered Jobs")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Source")
    table.add_column("Company", style="bold")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("Status")
    table.add_column("URL")

    for row in rows:
        table.add_row(
            str(row.id),
            row.source,
            row.company,
            row.title,
            row.location,
            row.status,
            row.url,
        )

    console.print(table)


@cli.command(name="mark-applied")
@click.argument("app_id", type=int)
@click.option("--notes", default="")
def mark_applied_cmd(app_id: int, notes: str):
    """Mark an application as applied."""
    ok = mark_applied(app_id, notes=notes)
    if ok:
        console.print(f"[green]Application #{app_id} marked as applied.[/green]")
    else:
        console.print(f"[red]Application #{app_id} not found.[/red]")


@cli.command(name="mark-interview")
@click.argument("app_id", type=int)
@click.option("--notes", default="")
def mark_interview_cmd(app_id: int, notes: str):
    """Mark an application as interview stage."""
    ok = mark_interview(app_id, notes=notes)
    if ok:
        console.print(f"[green]Application #{app_id} marked as interview.[/green]")
    else:
        console.print(f"[red]Application #{app_id} not found.[/red]")


@cli.command(name="mark-rejected")
@click.argument("app_id", type=int)
@click.option("--notes", default="")
def mark_rejected_cmd(app_id: int, notes: str):
    """Mark an application as rejected."""
    ok = mark_rejected(app_id, notes=notes)
    if ok:
        console.print(f"[green]Application #{app_id} marked as rejected.[/green]")
    else:
        console.print(f"[red]Application #{app_id} not found.[/red]")


@cli.command(name="stats")
def stats_cmd():
    """Show summary stats."""
    stats = get_summary_stats()
    latest_run = get_latest_discovery_run()

    lines = [
        f"Applications total: {stats.get('total', 0)}",
        f"Saved: {stats.get('saved', 0)}",
        f"Applied: {stats.get('applied', 0)}",
        f"Interview: {stats.get('interview', 0)}",
        f"Offer: {stats.get('offer', 0)}",
        f"Rejected: {stats.get('rejected', 0)}",
        f"Discovered jobs total: {stats.get('discovered_jobs_total', 0)}",
        f"Discovered jobs new: {stats.get('discovered_jobs_new', 0)}",
        f"Discovered jobs applied: {stats.get('discovered_jobs_applied', 0)}",
    ]

    if latest_run:
        lines.append(
            f"Latest discovery run: {latest_run.status} on {latest_run.run_date} "
            f"({latest_run.inserted_count} new, {latest_run.updated_count} updated)"
        )

    console.print(Panel("\n".join(lines), title="FastApply Stats", border_style="green"))


if __name__ == "__main__":
    cli()
