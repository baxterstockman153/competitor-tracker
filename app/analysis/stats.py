from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Company, JobChange, JobPosting, ScrapeRun


@dataclass
class CompanyStats:
    company_name: str
    active_jobs: int
    new_count: int
    removed_count: int
    updated_count: int
    net_change: int
    active_jobs_7d_ago: int | None
    wow_delta: int | None


@dataclass
class SummaryStats:
    total_active_jobs: int
    total_new: int
    total_removed: int
    total_updated: int
    total_net_change: int
    companies: list[CompanyStats]


def compute_company_stats(session: Session, company: Company, scrape_run: ScrapeRun) -> CompanyStats:
    active_jobs = session.scalar(
        select(func.count()).select_from(JobPosting).where(
            JobPosting.company_id == company.id,
            JobPosting.is_active == True,  # noqa: E712
        )
    ) or 0

    change_counts = dict(
        session.execute(
            select(JobChange.change_type, func.count()).where(
                JobChange.company_id == company.id,
                JobChange.scrape_run_id == scrape_run.id,
            ).group_by(JobChange.change_type)
        ).all()
    )

    new_count = change_counts.get("new", 0)
    removed_count = change_counts.get("removed", 0)
    updated_count = change_counts.get("updated", 0)
    net_change = new_count - removed_count

    # WoW approximation using first_seen_at / last_seen_at
    cutoff = scrape_run.started_at - timedelta(days=7)

    # Check if any scrape run exists 7+ days ago
    prior_run = session.scalar(
        select(ScrapeRun.id).where(ScrapeRun.started_at <= cutoff).limit(1)
    )

    if prior_run is None:
        active_jobs_7d_ago = None
        wow_delta = None
    else:
        active_jobs_7d_ago = session.scalar(
            select(func.count()).select_from(JobPosting).where(
                JobPosting.company_id == company.id,
                JobPosting.first_seen_at <= cutoff,
                JobPosting.last_seen_at >= cutoff,
            )
        ) or 0
        wow_delta = active_jobs - active_jobs_7d_ago

    return CompanyStats(
        company_name=company.name,
        active_jobs=active_jobs,
        new_count=new_count,
        removed_count=removed_count,
        updated_count=updated_count,
        net_change=net_change,
        active_jobs_7d_ago=active_jobs_7d_ago,
        wow_delta=wow_delta,
    )


def compute_summary_stats(session: Session, scrape_run: ScrapeRun) -> SummaryStats:
    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()

    company_stats = [compute_company_stats(session, c, scrape_run) for c in companies]

    return SummaryStats(
        total_active_jobs=sum(cs.active_jobs for cs in company_stats),
        total_new=sum(cs.new_count for cs in company_stats),
        total_removed=sum(cs.removed_count for cs in company_stats),
        total_updated=sum(cs.updated_count for cs in company_stats),
        total_net_change=sum(cs.net_change for cs in company_stats),
        companies=company_stats,
    )
