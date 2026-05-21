from sqlalchemy import select

from app.db.models import JobTag

from tests.conftest import make_job, scrape_with_jobs


class TestClassificationIntegration:
    def test_tags_created_on_scrape(self, session):
        jobs = [make_job("1", "Senior Software Engineer", description="Build HIPAA-compliant FHIR APIs")]
        scrape_with_jobs(session, jobs)

        tags = session.scalars(select(JobTag)).all()
        tag_dict = {t.tag_type: t.tag_value for t in tags if t.tag_type != "domain"}
        domain_tags = [t.tag_value for t in tags if t.tag_type == "domain"]

        assert tag_dict["function"] == "Eng"
        assert tag_dict["seniority"] == "Senior"
        assert tag_dict["seniority_track"] == "IC"
        assert "hipaa" in domain_tags
        assert "fhir" in domain_tags
        assert all(t.tag_source == "deterministic" for t in tags)

    def test_tags_replaced_on_update(self, session):
        jobs = [make_job("1", "Junior Engineer", description="Build web apps")]
        scrape_with_jobs(session, jobs)

        # Update with new description
        updated = [make_job("1", "Junior Engineer", description="Work on HIPAA billing systems")]
        scrape_with_jobs(session, updated)

        tags = session.scalars(select(JobTag)).all()
        domain_tags = [t.tag_value for t in tags if t.tag_type == "domain"]

        # Should have hipaa and rcm from new description, not duplicates
        assert "hipaa" in domain_tags
        assert "rcm" in domain_tags
        # No duplicate function/seniority tags
        function_tags = [t for t in tags if t.tag_type == "function"]
        assert len(function_tags) == 1

    def test_tag_source_is_deterministic(self, session):
        jobs = [make_job("1", "VP of Sales", description="Lead sales team for payer accounts")]
        scrape_with_jobs(session, jobs)

        tags = session.scalars(select(JobTag)).all()
        assert len(tags) > 0
        assert all(t.tag_source == "deterministic" for t in tags)
