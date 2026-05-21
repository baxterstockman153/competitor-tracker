from collections import defaultdict

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.db.models import Company, JobPosting, JobTag


def generate_jobs_report(
    session: Session,
    function_filter: str | None = None,
    domain_filter: str | None = None,
    group_by: str = "company",
) -> str:
    if group_by not in ("company", "function", "domain"):
        raise ValueError(f"Unsupported group_by: {group_by!r}. Must be one of: company, function, domain")

    query = (
        select(JobPosting, Company.name.label("company_name"))
        .join(Company, JobPosting.company_id == Company.id)
        .where(JobPosting.is_active == True)  # noqa: E712
    )

    if function_filter:
        query = query.where(
            exists().where(
                JobTag.job_posting_id == JobPosting.id,
                JobTag.tag_type == "function",
                func.lower(JobTag.tag_value) == function_filter.lower(),
            )
        )

    if domain_filter:
        query = query.where(
            exists().where(
                JobTag.job_posting_id == JobPosting.id,
                JobTag.tag_type == "domain",
                func.lower(JobTag.tag_value) == domain_filter.lower(),
            )
        )

    query = query.order_by(Company.name, JobPosting.title)
    rows = session.execute(query).all()

    # Header
    filters = []
    if function_filter:
        filters.append(f"function={function_filter}")
    if domain_filter:
        filters.append(f"domain={domain_filter}")

    lines = ["=== ACTIVE JOBS ==="]
    if filters:
        lines.append(f"Filters: {', '.join(filters)}")
    lines.append(f"Group by: {group_by}")
    lines.append("")

    if not rows:
        lines.append("No active jobs matched these filters.")
        return "\n".join(lines)

    jobs_with_company = [(row[0], row[1]) for row in rows]

    if group_by == "company":
        lines.extend(_group_by_company(jobs_with_company))
    elif group_by == "function":
        lines.extend(_group_by_tag(session, jobs_with_company, "function"))
    elif group_by == "domain":
        lines.extend(_group_by_tag(session, jobs_with_company, "domain"))

    return "\n".join(lines)


def _format_job_line(title: str, location: str | None, prefix: str = "") -> str:
    loc = f" — {location}" if location else ""
    return f"{prefix}- {title}{loc}"


def _group_by_company(jobs_with_company: list[tuple[JobPosting, str]]) -> list[str]:
    groups: dict[str, list[JobPosting]] = defaultdict(list)
    for job, company_name in jobs_with_company:
        groups[company_name].append(job)

    lines = []
    for company_name in sorted(groups):
        jobs = groups[company_name]
        lines.append(f"{company_name} — {len(jobs)} jobs")
        for job in jobs:
            lines.append(_format_job_line(job.title, job.location, prefix="  "))
        lines.append("")
    return lines


def _group_by_tag(
    session: Session,
    jobs_with_company: list[tuple[JobPosting, str]],
    tag_type: str,
) -> list[str]:
    job_ids = [job.id for job, _ in jobs_with_company]
    job_lookup = {job.id: (job, company_name) for job, company_name in jobs_with_company}

    # Get relevant tags for these jobs
    tags = session.execute(
        select(JobTag.job_posting_id, JobTag.tag_value).where(
            JobTag.job_posting_id.in_(job_ids),
            JobTag.tag_type == tag_type,
        )
    ).all()

    groups: dict[str, list[tuple[JobPosting, str]]] = defaultdict(list)
    tagged_ids: set[int] = set()

    for job_posting_id, tag_value in tags:
        if job_posting_id in job_lookup:
            tagged_ids.add(job_posting_id)
            job, company_name = job_lookup[job_posting_id]
            groups[tag_value].append((job, company_name))

    # Uncategorized: jobs without this tag type
    for job_id, (job, company_name) in job_lookup.items():
        if job_id not in tagged_ids:
            groups["Uncategorized"].append((job, company_name))

    lines = []
    for tag_value in sorted(groups, key=lambda k: (k == "Uncategorized", k)):
        entries = groups[tag_value]
        lines.append(f"{tag_value} — {len(entries)} jobs")
        for job, company_name in sorted(entries, key=lambda e: (e[1], e[0].title)):
            lines.append(_format_job_line(job.title, job.location, prefix=f"  {company_name}: "))
        lines.append("")
    return lines
