from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import JobChange, JobTag, ScrapeRun


_SEVERITY_ORDER = {"significant": 0, "notable": 1, "info": 2}


@dataclass
class StrategicSignal:
    company_name: str
    signal: str
    severity: str


def detect_signals(session: Session, scrape_run: ScrapeRun) -> list[StrategicSignal]:
    signals: list[StrategicSignal] = []

    # Get all new job changes for this scrape run, joined with company name
    new_changes = session.execute(
        select(
            JobChange.job_posting_id,
            JobChange.title,
            JobChange.company_id,
        ).where(
            JobChange.scrape_run_id == scrape_run.id,
            JobChange.change_type == "new",
        )
    ).all()

    if not new_changes:
        return signals

    job_ids = [row.job_posting_id for row in new_changes if row.job_posting_id is not None]
    if not job_ids:
        return signals

    # Build lookup: job_posting_id -> (company_id, title)
    change_info = {
        row.job_posting_id: (row.company_id, row.title)
        for row in new_changes
        if row.job_posting_id is not None
    }

    # Get company names
    from app.db.models import Company
    companies = {
        c.id: c.name
        for c in session.scalars(select(Company)).all()
    }

    # Get all tags for these new jobs
    tags = session.execute(
        select(JobTag.job_posting_id, JobTag.tag_type, JobTag.tag_value).where(
            JobTag.job_posting_id.in_(job_ids)
        )
    ).all()

    # Leadership hires: VP or C-Suite seniority
    for tag in tags:
        if tag.tag_type == "seniority" and tag.tag_value in ("VP", "C-Suite"):
            company_id, title = change_info[tag.job_posting_id]
            company_name = companies.get(company_id, "Unknown")
            signals.append(StrategicSignal(
                company_name=company_name,
                signal=f"{company_name} added {tag.tag_value} {title}",
                severity="significant",
            ))

    # Build per-company tag groupings for domain and function clusters
    # company_id -> tag_value -> count
    domain_counts: dict[int, dict[str, int]] = {}
    function_counts: dict[int, dict[str, int]] = {}

    for tag in tags:
        company_id = change_info[tag.job_posting_id][0]
        if tag.tag_type == "domain":
            domain_counts.setdefault(company_id, {})
            domain_counts[company_id][tag.tag_value] = domain_counts[company_id].get(tag.tag_value, 0) + 1
        elif tag.tag_type == "function":
            function_counts.setdefault(company_id, {})
            function_counts[company_id][tag.tag_value] = function_counts[company_id].get(tag.tag_value, 0) + 1

    # Domain cluster: 2+ new jobs with same domain tag
    for company_id, counts in domain_counts.items():
        company_name = companies.get(company_id, "Unknown")
        for domain, count in counts.items():
            if count >= 2:
                signals.append(StrategicSignal(
                    company_name=company_name,
                    signal=f"{company_name} added {count} {domain} roles",
                    severity="notable",
                ))

    # Function burst: 3+ new jobs in same function
    for company_id, counts in function_counts.items():
        company_name = companies.get(company_id, "Unknown")
        for func, count in counts.items():
            if count >= 3:
                signals.append(StrategicSignal(
                    company_name=company_name,
                    signal=f"{company_name} added {count} {func} roles",
                    severity="notable",
                ))

    # Sort: significant first, then by company name
    signals.sort(key=lambda s: (_SEVERITY_ORDER.get(s.severity, 99), s.company_name))

    return signals
