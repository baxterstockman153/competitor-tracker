from datetime import datetime, timezone

import pytest

from app.db.models import Company, JobPosting, JobTag
from app.services.generate_jobs_report import generate_jobs_report


def _create_company(session, name="TestCo"):
    company = Company(name=name, careers_url="https://example.com", ats_provider="greenhouse")
    session.add(company)
    session.flush()
    return company


def _create_job(session, company, external_id, title, location=None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    job = JobPosting(
        company_id=company.id,
        external_id=external_id,
        title=title,
        location=location,
        current_description_hash="abc",
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    session.add(job)
    session.flush()
    return job


def _add_tag(session, job, tag_type, tag_value):
    tag = JobTag(
        job_posting_id=job.id,
        tag_type=tag_type,
        tag_value=tag_value,
        tag_source="deterministic",
    )
    session.add(tag)
    session.flush()
    return tag


class TestFilterByFunction:
    def test_filter_by_function(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Backend Engineer", "Remote")
        j2 = _create_job(session, co, "2", "Product Manager", "NYC")
        _add_tag(session, j1, "function", "Eng")
        _add_tag(session, j2, "function", "Product")

        report = generate_jobs_report(session, function_filter="Eng")
        assert "Backend Engineer" in report
        assert "Product Manager" not in report

    def test_filter_case_insensitive(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Backend Engineer")
        _add_tag(session, j1, "function", "Eng")

        report = generate_jobs_report(session, function_filter="eng")
        assert "Backend Engineer" in report


class TestFilterByDomain:
    def test_filter_by_domain(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Auth Engineer")
        j2 = _create_job(session, co, "2", "Billing Analyst")
        _add_tag(session, j1, "domain", "prior_auth")
        _add_tag(session, j2, "domain", "rcm")

        report = generate_jobs_report(session, domain_filter="prior_auth")
        assert "Auth Engineer" in report
        assert "Billing Analyst" not in report


class TestFilterByFunctionAndDomain:
    def test_filter_by_both(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Auth Engineer")
        j2 = _create_job(session, co, "2", "Auth PM")
        j3 = _create_job(session, co, "3", "Billing Engineer")
        _add_tag(session, j1, "function", "Eng")
        _add_tag(session, j1, "domain", "prior_auth")
        _add_tag(session, j2, "function", "Product")
        _add_tag(session, j2, "domain", "prior_auth")
        _add_tag(session, j3, "function", "Eng")
        _add_tag(session, j3, "domain", "rcm")

        report = generate_jobs_report(session, function_filter="Eng", domain_filter="prior_auth")
        assert "Auth Engineer" in report
        assert "Auth PM" not in report
        assert "Billing Engineer" not in report


class TestGroupByCompany:
    def test_group_by_company(self, session):
        co1 = _create_company(session, "AKASA")
        co2 = _create_company(session, "Cohere Health")
        _create_job(session, co1, "1", "Engineer A", "Remote")
        _create_job(session, co1, "2", "Engineer B")
        _create_job(session, co2, "3", "PM")

        report = generate_jobs_report(session, group_by="company")
        assert "AKASA — 2 jobs" in report
        assert "Cohere Health — 1 jobs" in report

    def test_includes_location(self, session):
        co = _create_company(session)
        _create_job(session, co, "1", "Engineer", "San Francisco")

        report = generate_jobs_report(session, group_by="company")
        assert "Engineer — San Francisco" in report


class TestGroupByFunction:
    def test_group_by_function(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Backend Engineer")
        j2 = _create_job(session, co, "2", "Frontend Engineer")
        j3 = _create_job(session, co, "3", "Product Manager")
        _add_tag(session, j1, "function", "Eng")
        _add_tag(session, j2, "function", "Eng")
        _add_tag(session, j3, "function", "Product")

        report = generate_jobs_report(session, group_by="function")
        assert "Eng — 2 jobs" in report
        assert "Product — 1 jobs" in report

    def test_uncategorized_jobs(self, session):
        co = _create_company(session)
        _create_job(session, co, "1", "Chief of Staff")
        # No function tag added

        report = generate_jobs_report(session, group_by="function")
        assert "Uncategorized — 1 jobs" in report


class TestGroupByDomain:
    def test_group_by_domain(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Auth Engineer")
        _add_tag(session, j1, "domain", "prior_auth")
        _add_tag(session, j1, "domain", "hipaa")

        report = generate_jobs_report(session, group_by="domain")
        # Job appears in both domain groups
        assert "prior_auth — 1 jobs" in report
        assert "hipaa — 1 jobs" in report

    def test_job_in_multiple_domain_groups(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Integration Engineer")
        _add_tag(session, j1, "domain", "fhir")
        _add_tag(session, j1, "domain", "ehr")

        report = generate_jobs_report(session, group_by="domain")
        assert "fhir" in report
        assert "ehr" in report


class TestNoMatches:
    def test_no_matches(self, session):
        co = _create_company(session)
        j1 = _create_job(session, co, "1", "Engineer")
        _add_tag(session, j1, "function", "Eng")

        report = generate_jobs_report(session, function_filter="Clinical")
        assert "No active jobs matched these filters." in report


class TestInvalidGroupBy:
    def test_invalid_group_by(self, session):
        with pytest.raises(ValueError, match="Unsupported group_by"):
            generate_jobs_report(session, group_by="seniority")


class TestDefaultReportUnchanged:
    def test_default_no_filters(self, session):
        co = _create_company(session)
        _create_job(session, co, "1", "Engineer", "Remote")

        report = generate_jobs_report(session)
        assert "=== ACTIVE JOBS ===" in report
        assert "Group by: company" in report
        assert "Engineer — Remote" in report
