from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, JobChange, ScrapeRun


@dataclass
class CompanyDiff:
    company_name: str
    new_jobs: list[str] = field(default_factory=list)
    removed_jobs: list[str] = field(default_factory=list)
    updated_jobs: list[str] = field(default_factory=list)


def compute_company_diff(session: Session, company: Company, scrape_run: ScrapeRun) -> CompanyDiff:
    diff = CompanyDiff(company_name=company.name)

    changes = session.scalars(
        select(JobChange).where(
            JobChange.company_id == company.id,
            JobChange.scrape_run_id == scrape_run.id,
        )
    ).all()

    for change in changes:
        if change.change_type == "new":
            diff.new_jobs.append(change.title)
        elif change.change_type == "removed":
            diff.removed_jobs.append(change.title)
        elif change.change_type == "updated":
            diff.updated_jobs.append(change.title)

    return diff
