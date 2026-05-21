from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.diff import compute_company_diff
from app.analysis.signals import detect_signals
from app.analysis.stats import compute_summary_stats
from app.db.models import Company, JobChange, JobPosting, ScrapeRun


def generate_weekly_report(session: Session) -> str:
    scrape_run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
    )
    if scrape_run is None:
        return "No scrape runs found. Run 'python main.py scrape' first."

    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()
    stats = compute_summary_stats(session, scrape_run)
    signals = detect_signals(session, scrape_run)
    diffs = {c.name: compute_company_diff(session, c, scrape_run) for c in companies}

    # Build location lookup for new/removed jobs via JobChange -> JobPosting
    location_lookup = _build_location_lookup(session, scrape_run)

    sections: list[str] = []

    # Section 1: Header
    end_date = scrape_run.started_at
    start_date = end_date - timedelta(days=7)
    sections.append(
        f"=== WEEKLY COMPETITOR HIRING REPORT ({start_date.strftime('%b %d')}–{end_date.strftime('%b %d, %Y')}) ==="
    )

    # Section 2: Headline Numbers
    sections.append(_headline_numbers(stats))

    # Section 3: Strategic Signals
    if signals:
        lines = ["", "STRATEGIC SIGNALS"]
        for s in signals:
            lines.append(f"[{s.severity}] {s.signal}")
        sections.append("\n".join(lines))

    # Section 4: Top Movers
    movers = _top_movers(stats)
    if movers:
        sections.append("\n" + movers)

    # Section 5: What's New
    new_section = _whats_new(diffs, location_lookup)
    if new_section:
        sections.append("\n" + new_section)

    # Section 6: What Closed
    closed_section = _whats_closed(diffs)
    if closed_section:
        sections.append("\n" + closed_section)

    return "\n".join(sections)


def _build_location_lookup(session: Session, scrape_run: ScrapeRun) -> dict[tuple[int, str], str | None]:
    """Map (company_id, title) -> location for changes in this scrape run."""
    rows = session.execute(
        select(JobChange.company_id, JobChange.title, JobPosting.location)
        .outerjoin(JobPosting, JobChange.job_posting_id == JobPosting.id)
        .where(JobChange.scrape_run_id == scrape_run.id)
    ).all()
    return {(row.company_id, row.title): row.location for row in rows}


def _headline_numbers(stats) -> str:
    lines = ["", "HEADLINE NUMBERS"]
    n_companies = len(stats.companies)

    wow_companies = [c for c in stats.companies if c.active_jobs_7d_ago is not None]
    if wow_companies:
        total_7d_ago = sum(c.active_jobs_7d_ago for c in wow_companies)
        wow_delta = stats.total_active_jobs - total_7d_ago
        lines.append(
            f"Total active across {n_companies} companies: {stats.total_active_jobs} ({wow_delta:+d} vs last week)"
        )
    else:
        lines.append(f"Total active across {n_companies} companies: {stats.total_active_jobs}")

    lines.append(
        f"New postings: {stats.total_new} | Removed: {stats.total_removed} | Net: {stats.total_net_change:+d}"
    )
    return "\n".join(lines)


def _top_movers(stats) -> str | None:
    movers = [c for c in stats.companies if c.net_change != 0]
    if not movers:
        return None

    movers.sort(key=lambda c: abs(c.net_change), reverse=True)

    lines = ["TOP MOVERS"]
    for c in movers:
        annotation = "net growth" if c.net_change > 0 else "net reduction"
        if c.wow_delta is not None:
            lines.append(f"{c.company_name}: {c.active_jobs} active ({c.wow_delta:+d} WoW) — {annotation}")
        else:
            lines.append(f"{c.company_name}: {c.active_jobs} active ({c.net_change:+d} net) — {annotation}")
    return "\n".join(lines)


def _whats_new(
    diffs: dict[str, object],
    location_lookup: dict[tuple[int, str], str | None],
) -> str | None:
    lines = ["WHAT'S NEW"]
    any_new = False

    title_to_location: dict[str, str | None] = {}
    for (_company_id, title), location in location_lookup.items():
        title_to_location[title] = location

    for company_name, diff in sorted(diffs.items()):
        if diff.new_jobs:
            any_new = True
            lines.append(f"{company_name}:")
            for title in diff.new_jobs:
                loc = title_to_location.get(title)
                loc_str = f" — {loc}" if loc else ""
                lines.append(f"  + {title}{loc_str}")

    if not any_new:
        return None
    return "\n".join(lines)


def _whats_closed(diffs: dict[str, object]) -> str | None:
    lines = ["WHAT CLOSED"]
    any_removed = False

    for company_name, diff in sorted(diffs.items()):
        if diff.removed_jobs:
            any_removed = True
            lines.append(f"{company_name}:")
            for title in diff.removed_jobs:
                lines.append(f"  - {title}")

    if not any_removed:
        return None
    return "\n".join(lines)
