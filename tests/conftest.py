from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import CompanyConfig
from app.db.models import ScrapeRun
from app.db.session import Base
from app.schemas.job import NormalizedJob
from app.services.scrape_company import scrape_company


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def make_config() -> CompanyConfig:
    return CompanyConfig(
        name="TestCo",
        careers_url="https://example.com/careers",
        ats_provider="greenhouse",
    )


def make_job(external_id: str, title: str, description: str = "desc") -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        title=title,
        description=description,
        url="https://example.com/jobs/" + external_id,
    )


def make_scrape_run(session) -> ScrapeRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ScrapeRun(started_at=now)
    session.add(run)
    session.flush()
    return run


def scrape_with_jobs(session, jobs: list[NormalizedJob]) -> ScrapeRun:
    run = make_scrape_run(session)
    with patch("app.services.scrape_company.get_scraper") as mock_get:
        mock_get.return_value.fetch_jobs.return_value = jobs
        scrape_company(session, make_config(), run)
    session.flush()
    return run
