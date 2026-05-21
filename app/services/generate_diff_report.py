from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.diff import compute_company_diff
from app.db.models import Company, ScrapeRun


def generate_report(session: Session) -> str:
    scrape_run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
    )
    if scrape_run is None:
        return "No scrape runs found. Run 'python main.py scrape' first."

    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()

    blocks: list[str] = []
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

    return "\n".join(blocks)
