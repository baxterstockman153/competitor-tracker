from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, JobPosting, JobSnapshot


@dataclass
class CompanyDiff:
    company_name: str
    new_jobs: list[str] = field(default_factory=list)
    removed_jobs: list[str] = field(default_factory=list)
    updated_jobs: list[str] = field(default_factory=list)


def compute_company_diff(session: Session, company: Company) -> CompanyDiff:
    diff = CompanyDiff(company_name=company.name)

    jobs = session.scalars(select(JobPosting).where(JobPosting.company_id == company.id)).all()

    for job in jobs:
        snapshots = session.scalars(
            select(JobSnapshot)
            .where(JobSnapshot.job_posting_id == job.id)
            .order_by(JobSnapshot.scraped_at.asc())
        ).all()

        if not snapshots:
            continue

        if len(snapshots) == 1:
            if job.is_active:
                diff.new_jobs.append(job.title)
            continue

        if not job.is_active:
            diff.removed_jobs.append(job.title)

        latest = snapshots[-1]
        previous = snapshots[-2]
        if latest.description_hash != previous.description_hash:
            diff.updated_jobs.append(job.title)

    return diff
