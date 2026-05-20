import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CompanyConfig
from app.db.models import Company, JobPosting, JobSnapshot
from app.scrapers.factory import get_scraper


def _hash_description(description: str) -> str:
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def scrape_company(session: Session, company_config: CompanyConfig) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    company = session.scalar(select(Company).where(Company.name == company_config.name))
    if company is None:
        company = Company(
            name=company_config.name,
            careers_url=company_config.careers_url,
            ats_provider=company_config.ats_provider,
        )
        session.add(company)
        session.flush()

    scraper = get_scraper(company_config.ats_provider)
    scraped_jobs = scraper.fetch_jobs(company_config.careers_url)

    existing_jobs = session.scalars(
        select(JobPosting).where(JobPosting.company_id == company.id)
    ).all()
    existing_by_external_id = {job.external_id: job for job in existing_jobs}

    seen_external_ids: set[str] = set()

    for scraped_job in scraped_jobs:
        seen_external_ids.add(scraped_job.external_id)
        description_hash = _hash_description(scraped_job.description)
        job = existing_by_external_id.get(scraped_job.external_id)

        if job is None:
            job = JobPosting(
                company_id=company.id,
                external_id=scraped_job.external_id,
                title=scraped_job.title,
                location=scraped_job.location,
                department=scraped_job.department,
                current_description_hash=description_hash,
                first_seen_at=now,
                last_seen_at=now,
                is_active=True,
            )
            session.add(job)
            session.flush()

            snapshot = JobSnapshot(
                job_posting_id=job.id,
                title=scraped_job.title,
                location=scraped_job.location,
                department=scraped_job.department,
                description=scraped_job.description,
                description_hash=description_hash,
                scraped_at=now,
            )
            session.add(snapshot)
            continue

        description_changed = job.current_description_hash != description_hash
        metadata_changed = (
            job.title != scraped_job.title
            or job.location != scraped_job.location
            or job.department != scraped_job.department
        )

        job.title = scraped_job.title
        job.location = scraped_job.location
        job.department = scraped_job.department
        job.last_seen_at = now
        job.is_active = True

        if description_changed:
            job.current_description_hash = description_hash

        if description_changed or metadata_changed:
            snapshot = JobSnapshot(
                job_posting_id=job.id,
                title=scraped_job.title,
                location=scraped_job.location,
                department=scraped_job.department,
                description=scraped_job.description,
                description_hash=description_hash,
                scraped_at=now,
            )
            session.add(snapshot)

    for existing_job in existing_jobs:
        if existing_job.external_id not in seen_external_ids:
            existing_job.is_active = False

    session.commit()
