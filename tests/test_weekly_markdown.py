from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select

from app.db.models import JobPosting, ScrapeRun
from app.services.generate_weekly_report import generate_weekly_report
from app.services.scrape_company import scrape_company

from tests.conftest import make_config, make_job, make_scrape_run, scrape_with_jobs


class TestMarkdownHeader:
    def test_markdown_has_h1_header(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "# Weekly Competitor Hiring Report" in result


class TestMarkdownHeadlineTable:
    def test_markdown_headline_table(self, session):
        jobs = [make_job("1", "Eng"), make_job("2", "PM"), make_job("3", "Designer")]
        scrape_with_jobs(session, jobs)
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Headline Numbers" in result
        assert "| Total active | 3 |" in result
        assert "| New postings | +3 |" in result


class TestMarkdownWow:
    def test_wow_row_present_when_available(self, session):
        ten_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
        old_run = ScrapeRun(started_at=ten_days_ago, completed_at=ten_days_ago)
        session.add(old_run)
        session.flush()

        jobs = [make_job("1", "Engineer")]
        with patch("app.services.scrape_company.get_scraper") as mock_get:
            mock_get.return_value.fetch_jobs.return_value = jobs
            scrape_company(session, make_config(), old_run)
        session.flush()

        for jp in session.scalars(select(JobPosting)).all():
            jp.first_seen_at = ten_days_ago
            jp.last_seen_at = ten_days_ago
        session.flush()

        scrape_with_jobs(session, [make_job("1", "Engineer"), make_job("2", "PM")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "| vs last week |" in result

    def test_wow_row_absent_when_no_history(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "vs last week" not in result


class TestMarkdownSignals:
    def test_signals_bold_severity(self, session):
        scrape_with_jobs(session, [make_job("1", "VP of Product", description="Lead product")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Strategic Signals" in result
        assert "**[significant]**" in result

    def test_signals_omitted_when_none(self, session):
        scrape_with_jobs(session, [make_job("1", "Software Engineer", description="Build things")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Strategic Signals" not in result


class TestMarkdownMovers:
    def test_movers_table(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        scrape_with_jobs(session, [make_job("1", "Engineer"), make_job("2", "PM"), make_job("3", "Designer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Top Movers" in result
        assert "| Company |" in result
        assert "net growth" in result

    def test_movers_omitted_when_flat(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Top Movers" not in result


class TestMarkdownNewJobs:
    def test_new_jobs_bold_company(self, session):
        scrape_with_jobs(session, [make_job("1", "Backend Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## What's New" in result
        assert "**TestCo**" in result
        assert "- Backend Engineer" in result


class TestMarkdownRemovedJobs:
    def test_removed_jobs(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer"), make_job("2", "Designer")])
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## What Closed" in result
        assert "- Designer" in result


class TestMarkdownEmptySections:
    def test_empty_sections_omitted(self, session):
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        scrape_with_jobs(session, [make_job("1", "Engineer")])
        result = generate_weekly_report(session, output_format="markdown")
        assert "## Headline Numbers" in result
        assert "## Strategic Signals" not in result
        assert "## Top Movers" not in result
        assert "## What's New" not in result
        assert "## What Closed" not in result
