from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select

from app.config import CompanyConfig
from app.db.models import Company, JobChange, JobPosting, ScrapeRun
from app.schemas.job import NormalizedJob
from app.services.scrape_company import scrape_company


def _make_config() -> CompanyConfig:
    return CompanyConfig(
        name="TestCo",
        careers_url="https://example.com/careers",
        ats_provider="greenhouse",
    )


def _make_job(external_id: str, title: str, description: str = "desc") -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        title=title,
        description=description,
        url="https://example.com/jobs/" + external_id,
    )


def _make_scrape_run(session) -> ScrapeRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ScrapeRun(started_at=now)
    session.add(run)
    session.flush()
    return run


def _scrape_with_jobs(session, jobs: list[NormalizedJob]) -> ScrapeRun:
    run = _make_scrape_run(session)
    with patch("app.services.scrape_company.get_scraper") as mock_get:
        mock_get.return_value.fetch_jobs.return_value = jobs
        scrape_company(session, _make_config(), run)
    session.flush()
    return run


class TestNewJobsDetected:
    def test_new_jobs_on_first_scrape(self, session):
        jobs = [_make_job("1", "Engineer"), _make_job("2", "Designer")]
        run = _scrape_with_jobs(session, jobs)

        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run.id)
        ).all()
        assert len(changes) == 2
        assert all(c.change_type == "new" for c in changes)


class TestNewJobsNotRepeated:
    def test_no_new_changes_on_second_scrape(self, session):
        jobs = [_make_job("1", "Engineer"), _make_job("2", "Designer")]
        _scrape_with_jobs(session, jobs)

        run2 = _scrape_with_jobs(session, jobs)
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 0


class TestRemovedJobsDetected:
    def test_removed_job_creates_change(self, session):
        jobs = [_make_job("1", "Engineer")]
        _scrape_with_jobs(session, jobs)

        run2 = _scrape_with_jobs(session, [])
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].title == "Engineer"


class TestUpdatedJobsDetected:
    def test_updated_description_creates_change(self, session):
        jobs = [_make_job("1", "Engineer", description="old description")]
        _scrape_with_jobs(session, jobs)

        updated_jobs = [_make_job("1", "Engineer", description="new description")]
        run2 = _scrape_with_jobs(session, updated_jobs)

        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 1
        assert changes[0].change_type == "updated"


class TestNoChangeProducesEmptyReport:
    def test_identical_scrape_no_changes(self, session):
        jobs = [_make_job("1", "Engineer"), _make_job("2", "Designer")]
        _scrape_with_jobs(session, jobs)

        run2 = _scrape_with_jobs(session, jobs)
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 0
