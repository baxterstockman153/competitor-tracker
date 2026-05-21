from datetime import datetime, timezone

from sqlalchemy import select

from app.analysis.signals import detect_signals
from app.db.models import Company, JobChange, JobPosting, JobTag, ScrapeRun

from tests.conftest import make_scrape_run


def _setup_company(session, name="TestCo"):
    company = Company(name=name, careers_url="https://example.com", ats_provider="greenhouse")
    session.add(company)
    session.flush()
    return company


def _add_new_job_with_tags(session, company, scrape_run, title, tags_dict):
    """Create a JobPosting, a 'new' JobChange, and JobTag rows."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    job = JobPosting(
        company_id=company.id,
        external_id=f"ext-{title}",
        title=title,
        current_description_hash="abc",
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    session.add(job)
    session.flush()

    change = JobChange(
        company_id=company.id,
        job_posting_id=job.id,
        scrape_run_id=scrape_run.id,
        change_type="new",
        title=title,
        created_at=now,
    )
    session.add(change)

    for tag_type, tag_value in tags_dict.items():
        if isinstance(tag_value, list):
            for v in tag_value:
                session.add(JobTag(
                    job_posting_id=job.id, tag_type=tag_type, tag_value=v, tag_source="deterministic"
                ))
        else:
            session.add(JobTag(
                job_posting_id=job.id, tag_type=tag_type, tag_value=tag_value, tag_source="deterministic"
            ))
    session.flush()
    return job


class TestNoSignalSingleNewJob:
    def test_no_signal_single_new_job(self, session):
        company = _setup_company(session)
        run = make_scrape_run(session)
        _add_new_job_with_tags(session, company, run, "Engineer", {
            "function": "Eng", "seniority": "Mid", "seniority_track": "IC", "geography": "Remote",
        })
        signals = detect_signals(session, run)
        assert len(signals) == 0


class TestSignalOnDomainCluster:
    def test_signal_on_domain_cluster(self, session):
        company = _setup_company(session)
        run = make_scrape_run(session)
        _add_new_job_with_tags(session, company, run, "Auth Eng 1", {
            "function": "Eng", "seniority": "Mid", "domain": ["prior_auth"],
        })
        _add_new_job_with_tags(session, company, run, "Auth Eng 2", {
            "function": "Eng", "seniority": "Mid", "domain": ["prior_auth"],
        })
        signals = detect_signals(session, run)
        domain_signals = [s for s in signals if "prior_auth" in s.signal]
        assert len(domain_signals) == 1
        assert domain_signals[0].severity == "notable"


class TestSignalOnVpHire:
    def test_signal_on_vp_hire(self, session):
        company = _setup_company(session)
        run = make_scrape_run(session)
        _add_new_job_with_tags(session, company, run, "VP Product", {
            "function": "Product", "seniority": "VP", "seniority_track": "Mgmt",
        })
        signals = detect_signals(session, run)
        vp_signals = [s for s in signals if "VP" in s.signal]
        assert len(vp_signals) == 1
        assert vp_signals[0].severity == "significant"


class TestSignalOnFunctionBurst:
    def test_signal_on_function_burst(self, session):
        company = _setup_company(session)
        run = make_scrape_run(session)
        for i in range(3):
            _add_new_job_with_tags(session, company, run, f"Engineer {i}", {
                "function": "Eng", "seniority": "Mid",
            })
        signals = detect_signals(session, run)
        eng_signals = [s for s in signals if "Eng" in s.signal]
        assert len(eng_signals) == 1
        assert eng_signals[0].severity == "notable"


class TestSignalsSortedBySeverity:
    def test_signals_sorted_by_severity(self, session):
        company = _setup_company(session)
        run = make_scrape_run(session)
        # Create a function burst (notable)
        for i in range(3):
            _add_new_job_with_tags(session, company, run, f"Engineer {i}", {
                "function": "Eng", "seniority": "Mid",
            })
        # Create a VP hire (significant)
        _add_new_job_with_tags(session, company, run, "VP Engineering", {
            "function": "Eng", "seniority": "VP", "seniority_track": "Mgmt",
        })
        signals = detect_signals(session, run)
        assert len(signals) >= 2
        assert signals[0].severity == "significant"
