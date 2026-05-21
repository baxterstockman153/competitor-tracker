from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select

from app.config import CompanyConfig
from app.db.models import Company, JobPosting, JobTag, ScrapeRun
from app.services.generate_weekly_report import generate_weekly_report
from app.services.scrape_company import scrape_company

from tests.conftest import make_config, make_job, make_scrape_run, scrape_with_jobs


class TestNoScrapeRuns:
    def test_no_scrape_runs(self, session):
        result = generate_weekly_report(session)
        assert "No scrape runs found" in result


class TestHeadlineNumbers:
    def test_headline_numbers(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer"), make_job("3", "PM")]
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "HEADLINE NUMBERS" in result
        assert "Total active across 1 companies: 3" in result
        assert "New postings: 3" in result


class TestWowShownWhenAvailable:
    def test_wow_shown_when_available(self, session):
        # Old scrape run 10 days ago
        ten_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
        old_run = ScrapeRun(started_at=ten_days_ago, completed_at=ten_days_ago)
        session.add(old_run)
        session.flush()

        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        with patch("app.services.scrape_company.get_scraper") as mock_get:
            mock_get.return_value.fetch_jobs.return_value = jobs
            scrape_company(session, make_config(), old_run)
        session.flush()

        # Backdate jobs
        for jp in session.scalars(select(JobPosting)).all():
            jp.first_seen_at = ten_days_ago
            jp.last_seen_at = ten_days_ago
        session.flush()

        # Current scrape with 3 jobs
        current_jobs = [make_job("1", "Engineer"), make_job("2", "Designer"), make_job("3", "PM")]
        scrape_with_jobs(session, current_jobs)

        result = generate_weekly_report(session)
        assert "vs last week" in result


class TestWowOmittedWhenNoHistory:
    def test_wow_omitted_when_no_history(self, session):
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "vs last week" not in result


class TestSignalsSectionPresent:
    def test_signals_section_present(self, session):
        jobs = [make_job("1", "VP of Product", description="Lead product strategy")]
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "STRATEGIC SIGNALS" in result
        assert "VP" in result


class TestSignalsSectionOmitted:
    def test_signals_section_omitted(self, session):
        jobs = [make_job("1", "Software Engineer", description="Build things")]
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "STRATEGIC SIGNALS" not in result


class TestTopMovers:
    def test_top_movers_shown(self, session):
        # First scrape: 1 job
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        # Second scrape: 3 jobs (2 new)
        jobs2 = [make_job("1", "Engineer"), make_job("2", "Designer"), make_job("3", "PM")]
        scrape_with_jobs(session, jobs2)

        result = generate_weekly_report(session)
        assert "TOP MOVERS" in result
        assert "net growth" in result

    def test_top_movers_omitted_when_no_changes(self, session):
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        # Second scrape with same jobs — no changes
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "TOP MOVERS" not in result


class TestWhatsNew:
    def test_new_jobs_with_location(self, session):
        jobs = [
            make_job("1", "Backend Engineer", description="Build APIs"),
        ]
        # Use a job with location by creating it through scraper
        # The NormalizedJob doesn't have location easily, so we verify title appears
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "WHAT'S NEW" in result
        assert "Backend Engineer" in result

    def test_new_jobs_show_location(self, session):
        """Verify location appears when job has one."""
        jobs = [make_job("1", "Backend Engineer")]
        scrape_with_jobs(session, jobs)

        # Manually set location on the job posting
        jp = session.scalar(select(JobPosting))
        jp.location = "Remote"
        session.flush()

        result = generate_weekly_report(session)
        assert "Remote" in result


class TestWhatsClosed:
    def test_removed_jobs_shown(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        scrape_with_jobs(session, jobs)

        # Remove Designer
        scrape_with_jobs(session, [make_job("1", "Engineer")])

        result = generate_weekly_report(session)
        assert "WHAT CLOSED" in result
        assert "Designer" in result


class TestEmptySectionsOmitted:
    def test_empty_sections_omitted(self, session):
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        # Second scrape with same jobs — no new, no removed, no signals
        scrape_with_jobs(session, jobs)

        result = generate_weekly_report(session)
        assert "HEADLINE NUMBERS" in result
        assert "STRATEGIC SIGNALS" not in result
        assert "TOP MOVERS" not in result
        assert "WHAT'S NEW" not in result
        assert "WHAT CLOSED" not in result
