from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select

from app.analysis.stats import compute_company_stats, compute_summary_stats
from app.config import CompanyConfig
from app.db.models import Company, JobPosting, ScrapeRun
from app.services.scrape_company import scrape_company

from tests.conftest import make_config, make_job, make_scrape_run, scrape_with_jobs


class TestActiveJobsCount:
    def test_active_jobs_count(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer"), make_job("3", "PM")]
        run = scrape_with_jobs(session, jobs)
        company = session.scalar(select(Company))
        stats = compute_company_stats(session, company, run)
        assert stats.active_jobs == 3


class TestNewRemovedCounts:
    def test_new_removed_counts(self, session):
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        scrape_with_jobs(session, jobs)

        run2 = scrape_with_jobs(session, [make_job("1", "Engineer")])
        company = session.scalar(select(Company))
        stats = compute_company_stats(session, company, run2)
        assert stats.new_count == 0
        assert stats.removed_count == 1


class TestNetChange:
    def test_net_change(self, session):
        jobs = [make_job("1", "Engineer")]
        scrape_with_jobs(session, jobs)

        run2 = scrape_with_jobs(session, [make_job("1", "Engineer"), make_job("2", "New Role"), make_job("3", "Another")])
        company = session.scalar(select(Company))
        stats = compute_company_stats(session, company, run2)
        assert stats.net_change == stats.new_count - stats.removed_count
        assert stats.net_change == 2


class TestSummaryAggregatesAcrossCompanies:
    def test_summary_aggregates_across_companies(self, session):
        config_a = CompanyConfig(name="CompA", careers_url="https://a.com", ats_provider="greenhouse")
        config_b = CompanyConfig(name="CompB", careers_url="https://b.com", ats_provider="greenhouse")

        run = make_scrape_run(session)
        jobs_a = [make_job("1", "Eng A"), make_job("2", "Eng A2")]
        jobs_b = [make_job("3", "Eng B")]

        with patch("app.services.scrape_company.get_scraper") as mock_get:
            mock_get.return_value.fetch_jobs.return_value = jobs_a
            scrape_company(session, config_a, run)
            mock_get.return_value.fetch_jobs.return_value = jobs_b
            scrape_company(session, config_b, run)
        session.flush()

        stats = compute_summary_stats(session, run)
        assert stats.total_active_jobs == 3
        assert stats.total_new == 3
        assert len(stats.companies) == 2


class TestWowNoneWhenNoPriorRun:
    def test_wow_none_when_no_prior_run(self, session):
        jobs = [make_job("1", "Engineer")]
        run = scrape_with_jobs(session, jobs)
        company = session.scalar(select(Company))
        stats = compute_company_stats(session, company, run)
        assert stats.active_jobs_7d_ago is None
        assert stats.wow_delta is None


class TestWowComputedWithPriorData:
    def test_wow_computed_with_prior_data(self, session):
        # Create an old scrape run 10 days ago
        ten_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
        old_run = ScrapeRun(started_at=ten_days_ago, completed_at=ten_days_ago)
        session.add(old_run)
        session.flush()

        # Create jobs that existed 10 days ago
        jobs = [make_job("1", "Engineer"), make_job("2", "Designer")]
        with patch("app.services.scrape_company.get_scraper") as mock_get:
            mock_get.return_value.fetch_jobs.return_value = jobs
            scrape_company(session, make_config(), old_run)
        session.flush()

        # Backdate first_seen_at and last_seen_at
        for jp in session.scalars(select(JobPosting)).all():
            jp.first_seen_at = ten_days_ago
            jp.last_seen_at = ten_days_ago
        session.flush()

        # Now run a current scrape with 3 jobs (2 existing + 1 new)
        current_jobs = [make_job("1", "Engineer"), make_job("2", "Designer"), make_job("3", "PM")]
        run2 = scrape_with_jobs(session, current_jobs)

        company = session.scalar(select(Company))
        stats = compute_company_stats(session, company, run2)
        assert stats.active_jobs == 3
        assert stats.active_jobs_7d_ago == 2
        assert stats.wow_delta == 1
