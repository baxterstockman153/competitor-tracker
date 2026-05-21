from sqlalchemy import select

from app.db.models import JobChange

from tests.conftest import make_job, scrape_with_jobs


class TestNewJobsDetected:
    def test_new_jobs_on_first_scrape(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        run = scrape_with_jobs(session, jobs)

        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run.id)
        ).all()
        assert len(changes) == 2
        assert all(c.change_type == "new" for c in changes)


class TestNewJobsNotRepeated:
    def test_no_new_changes_on_second_scrape(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        scrape_with_jobs(session, jobs)

        run2 = scrape_with_jobs(session, jobs)
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 0


class TestRemovedJobsDetected:
    def test_removed_job_creates_change(self, session):
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        run2 = scrape_with_jobs(session, [])
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].title == "Engineer"


class TestUpdatedJobsDetected:
    def test_updated_description_creates_change(self, session):
        jobs = [make_job("1", "Engineer", description="old description")]
        scrape_with_jobs(session, jobs)

        updated_jobs = [make_job("1", "Engineer", description="new description")]
        run2 = scrape_with_jobs(session, updated_jobs)

        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 1
        assert changes[0].change_type == "updated"


class TestNoChangeProducesEmptyReport:
    def test_identical_scrape_no_changes(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        scrape_with_jobs(session, jobs)

        run2 = scrape_with_jobs(session, jobs)
        changes = session.scalars(
            select(JobChange).where(JobChange.scrape_run_id == run2.id)
        ).all()
        assert len(changes) == 0
