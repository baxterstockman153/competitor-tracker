from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.diff import compute_company_diff
from app.analysis.signals import detect_signals
from app.analysis.stats import compute_summary_stats
from app.db.models import Company, ScrapeRun


def generate_report(session: Session) -> str:
    scrape_run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
    )
    if scrape_run is None:
        return "No scrape runs found. Run 'python main.py scrape' first."

    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()

    # Summary stats block
    stats = compute_summary_stats(session, scrape_run)
    timestamp = scrape_run.started_at.strftime("%Y-%m-%d %H:%M UTC")
    blocks: list[str] = [
        f"=== SUMMARY ({timestamp}) ===",
        f"Total active: {stats.total_active_jobs} | New: +{stats.total_new} | Removed: -{stats.total_removed} | Net: {stats.total_net_change:+d}",
    ]

    wow_companies = [c for c in stats.companies if c.active_jobs_7d_ago is not None]
    if wow_companies:
        total_7d_ago = sum(c.active_jobs_7d_ago for c in wow_companies)
        wow_total = stats.total_active_jobs - total_7d_ago
        blocks.append(f"Week-over-week: {stats.total_active_jobs} vs {total_7d_ago} ({wow_total:+d})")

    blocks.append("")

    # Per-company diffs
    for company in companies:
        diff = compute_company_diff(session, company, scrape_run)
        lines = [
            "=" * 50,
            diff.company_name,
            "=" * 50,
            "",
            "NEW:",
        ]
        lines.extend(f"- {title}" for title in diff.new_jobs) if diff.new_jobs else lines.append("- None")
        lines.append("")
        lines.append("REMOVED:")
        lines.extend(f"- {title}" for title in diff.removed_jobs) if diff.removed_jobs else lines.append("- None")
        lines.append("")
        lines.append("UPDATED:")
        lines.extend(f"- {title}\n  Description changed" for title in diff.updated_jobs) if diff.updated_jobs else lines.append("- None")
        lines.append("")
        blocks.append("\n".join(lines))

    # Strategic signals
    signals = detect_signals(session, scrape_run)
    if signals:
        signal_lines = [
            "=" * 50,
            "STRATEGIC SIGNALS",
            "=" * 50,
        ]
        for s in signals:
            signal_lines.append(f"[{s.severity}] {s.signal}")
        blocks.append("\n".join(signal_lines))

    return "\n".join(blocks)
