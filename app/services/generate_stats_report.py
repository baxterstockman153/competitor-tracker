from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.stats import compute_summary_stats
from app.db.models import ScrapeRun


def generate_stats_report(session: Session) -> str:
    scrape_run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
    )
    if scrape_run is None:
        return "No scrape runs found. Run 'python main.py scrape' first."

    stats = compute_summary_stats(session, scrape_run)

    timestamp = scrape_run.started_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"=== SUMMARY ({timestamp}) ===",
        f"Total active: {stats.total_active_jobs} | New: +{stats.total_new} | Removed: -{stats.total_removed} | Net: {stats.total_net_change:+d}",
    ]

    # WoW line if any company has data
    wow_companies = [c for c in stats.companies if c.active_jobs_7d_ago is not None]
    if wow_companies:
        total_7d_ago = sum(c.active_jobs_7d_ago for c in wow_companies)
        wow_total = stats.total_active_jobs - total_7d_ago
        lines.append(f"Week-over-week: {stats.total_active_jobs} vs {total_7d_ago} ({wow_total:+d})")

    lines.append("")

    # Table header
    lines.append(f"{'Company':<25} {'Active':>6} {'New':>5} {'Removed':>8} {'Updated':>8} {'Net':>5} {'WoW':>5}")
    lines.append(f"{'-' * 25} {'-' * 6} {'-' * 5} {'-' * 8} {'-' * 8} {'-' * 5} {'-' * 5}")

    for cs in stats.companies:
        wow_str = f"{cs.wow_delta:+d}" if cs.wow_delta is not None else "N/A"
        lines.append(
            f"{cs.company_name:<25} {cs.active_jobs:>6} {cs.new_count:>+5} {cs.removed_count:>8} {cs.updated_count:>8} {cs.net_change:>+5} {wow_str:>5}"
        )

    return "\n".join(lines)
