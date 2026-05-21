from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.diff import compute_company_diff
from app.analysis.signals import StrategicSignal, detect_signals
from app.analysis.stats import CompanyStats, SummaryStats, compute_summary_stats
from app.db.models import Company, JobChange, JobPosting, ScrapeRun

# Location lookup keyed by (company_name, title) to avoid collisions
# when two companies have jobs with the same title.
LocationLookup = dict[tuple[str, str], str | None]


@dataclass
class WeeklyReportData:
    start_date: datetime
    end_date: datetime
    stats: SummaryStats
    signals: list[StrategicSignal]
    movers: list[CompanyStats]
    new_jobs: dict[str, list[tuple[str, str | None]]]  # company -> [(title, location)]
    removed_jobs: dict[str, list[str]]  # company -> [title]


def build_weekly_report_data(session: Session) -> WeeklyReportData | None:
    scrape_run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
    )
    if scrape_run is None:
        return None

    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()
    stats = compute_summary_stats(session, scrape_run)
    signals = detect_signals(session, scrape_run)
    diffs = {c.name: compute_company_diff(session, c, scrape_run) for c in companies}

    # Location lookup keyed by (company_name, title)
    rows = session.execute(
        select(Company.name, JobChange.title, JobPosting.location)
        .join(Company, JobChange.company_id == Company.id)
        .outerjoin(JobPosting, JobChange.job_posting_id == JobPosting.id)
        .where(JobChange.scrape_run_id == scrape_run.id)
    ).all()
    location_lookup: LocationLookup = {
        (row.name, row.title): row.location for row in rows
    }

    # Movers
    movers = [c for c in stats.companies if c.net_change != 0]
    movers.sort(key=lambda c: abs(c.net_change), reverse=True)

    # New jobs
    new_jobs: dict[str, list[tuple[str, str | None]]] = {}
    for company_name, diff in sorted(diffs.items()):
        if diff.new_jobs:
            new_jobs[company_name] = [
                (title, location_lookup.get((company_name, title))) for title in diff.new_jobs
            ]

    # Removed jobs
    removed_jobs: dict[str, list[str]] = {}
    for company_name, diff in sorted(diffs.items()):
        if diff.removed_jobs:
            removed_jobs[company_name] = diff.removed_jobs

    return WeeklyReportData(
        start_date=scrape_run.started_at - timedelta(days=7),
        end_date=scrape_run.started_at,
        stats=stats,
        signals=signals,
        movers=movers,
        new_jobs=new_jobs,
        removed_jobs=removed_jobs,
    )


def format_weekly_text(data: WeeklyReportData) -> str:
    sections: list[str] = []

    # Header
    sections.append(
        f"=== WEEKLY COMPETITOR HIRING REPORT ({data.start_date.strftime('%b %d')}–{data.end_date.strftime('%b %d, %Y')}) ==="
    )

    # Headline Numbers
    stats = data.stats
    lines = ["", "HEADLINE NUMBERS"]
    n_companies = len(stats.companies)
    wow_companies = [c for c in stats.companies if c.active_jobs_7d_ago is not None]
    if wow_companies:
        total_7d_ago = sum(c.active_jobs_7d_ago for c in wow_companies)
        wow_delta = stats.total_active_jobs - total_7d_ago
        lines.append(f"Total active across {n_companies} companies: {stats.total_active_jobs} ({wow_delta:+d} vs last week)")
    else:
        lines.append(f"Total active across {n_companies} companies: {stats.total_active_jobs}")
    lines.append(f"New postings: {stats.total_new} | Removed: {stats.total_removed} | Net: {stats.total_net_change:+d}")
    sections.append("\n".join(lines))

    # Strategic Signals
    if data.signals:
        lines = ["", "STRATEGIC SIGNALS"]
        for s in data.signals:
            lines.append(f"[{s.severity}] {s.signal}")
        sections.append("\n".join(lines))

    # Top Movers
    if data.movers:
        lines = ["", "TOP MOVERS"]
        for c in data.movers:
            annotation = "net growth" if c.net_change > 0 else "net reduction"
            if c.wow_delta is not None:
                lines.append(f"{c.company_name}: {c.active_jobs} active ({c.wow_delta:+d} WoW) — {annotation}")
            else:
                lines.append(f"{c.company_name}: {c.active_jobs} active ({c.net_change:+d} net) — {annotation}")
        sections.append("\n".join(lines))

    # What's New
    if data.new_jobs:
        lines = ["", "WHAT'S NEW"]
        for company_name, jobs in sorted(data.new_jobs.items()):
            lines.append(f"{company_name}:")
            for title, location in jobs:
                loc_str = f" — {location}" if location else ""
                lines.append(f"  + {title}{loc_str}")
        sections.append("\n".join(lines))

    # What Closed
    if data.removed_jobs:
        lines = ["", "WHAT CLOSED"]
        for company_name, titles in sorted(data.removed_jobs.items()):
            lines.append(f"{company_name}:")
            for title in titles:
                lines.append(f"  - {title}")
        sections.append("\n".join(lines))

    return "\n".join(sections)


def generate_weekly_report(session: Session, output_format: str = "text") -> str:
    if output_format not in ("text", "markdown"):
        raise ValueError(f"Unsupported output format: {output_format!r}. Must be 'text' or 'markdown'.")

    data = build_weekly_report_data(session)
    if data is None:
        return "No scrape runs found. Run 'python main.py scrape' first."

    if output_format == "markdown":
        from app.services.format_weekly_markdown import format_weekly_markdown
        return format_weekly_markdown(data)

    return format_weekly_text(data)
