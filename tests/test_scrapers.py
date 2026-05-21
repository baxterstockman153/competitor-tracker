from unittest.mock import MagicMock, patch

import pytest

from app.scrapers.ashby import AshbyScraper
from app.scrapers.workday import WorkdayScraper
from app.scrapers.custom import CustomScraper
from app.scrapers.factory import get_scraper


# --- Ashby Tests ---

ASHBY_RESPONSE = {
    "jobs": [
        {
            "id": "abc-123",
            "title": "Software Engineer",
            "location": "San Francisco, CA",
            "department": "Engineering",
            "descriptionPlain": "Build great software.",
            "jobUrl": "https://jobs.ashbyhq.com/notable/abc-123",
        },
        {
            "id": "def-456",
            "title": "Data Scientist",
            "location": "Remote",
            "department": "Data",
            "descriptionPlain": "",
            "descriptionHtml": "<p>Analyze <b>data</b> effectively.</p>",
            "jobUrl": "https://jobs.ashbyhq.com/notable/def-456",
        },
    ]
}


@patch("app.scrapers.ashby.requests.get")
def test_ashby_scraper_basic(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = ASHBY_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    scraper = AshbyScraper()
    jobs = scraper.fetch_jobs("https://api.ashbyhq.com/posting-api/job-board/notable")

    assert len(jobs) == 2
    assert jobs[0].external_id == "abc-123"
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].location == "San Francisco, CA"
    assert jobs[0].department == "Engineering"
    assert jobs[0].description == "Build great software."


@patch("app.scrapers.ashby.requests.get")
def test_ashby_html_fallback(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = ASHBY_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    scraper = AshbyScraper()
    jobs = scraper.fetch_jobs("https://api.ashbyhq.com/posting-api/job-board/notable")

    assert jobs[1].description == "Analyze data effectively."


# --- Workday Tests ---

WORKDAY_PAGE1 = {
    "total": 25,
    "jobPostings": [
        {
            "title": "Nurse Practitioner",
            "externalPath": "/job/Nurse-Practitioner_R1001",
            "locationsText": "New York, NY",
            "bulletFields": ["Full-time", "Healthcare"],
        },
    ] * 20,
}

WORKDAY_PAGE2 = {
    "total": 25,
    "jobPostings": [
        {
            "title": "Designer",
            "externalPath": "/job/Designer_R1003",
            "locationsText": "Austin, TX",
            "bulletFields": [],
        },
    ] * 5,
}

WORKDAY_URL = "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/jobs"


@patch("app.scrapers.workday.requests.post")
def test_workday_pagination(mock_post):
    resp1 = MagicMock()
    resp1.json.return_value = WORKDAY_PAGE1
    resp1.raise_for_status = MagicMock()

    resp2 = MagicMock()
    resp2.json.return_value = WORKDAY_PAGE2
    resp2.raise_for_status = MagicMock()

    mock_post.side_effect = [resp1, resp2]

    scraper = WorkdayScraper()
    jobs = scraper.fetch_jobs(WORKDAY_URL)

    assert len(jobs) == 25
    assert mock_post.call_count == 2


@patch("app.scrapers.workday.requests.post")
def test_workday_field_mapping(mock_post):
    resp = MagicMock()
    resp.json.return_value = {
        "total": 1,
        "jobPostings": [
            {
                "title": "Nurse Practitioner",
                "externalPath": "/job/Nurse-Practitioner_R1001",
                "locationsText": "New York, NY",
                "bulletFields": ["Full-time", "Healthcare"],
            },
        ],
    }
    resp.raise_for_status = MagicMock()
    mock_post.return_value = resp

    scraper = WorkdayScraper()
    jobs = scraper.fetch_jobs(WORKDAY_URL)

    assert jobs[0].external_id == "R1001"
    assert jobs[0].title == "Nurse Practitioner"
    assert jobs[0].location == "New York, NY"
    assert jobs[0].department is None
    assert jobs[0].description == "Full-time | Healthcare"
    assert str(jobs[0].url) == "https://acme.wd5.myworkdayjobs.com/job/Nurse-Practitioner_R1001"


# --- Custom HTML Tests ---

SAMPLE_HTML = """
<html><body>
<div class="job">
    <a href="/careers/engineer"><span class="title">Engineer</span></a>
    <span class="loc">NYC</span>
    <span class="dept">Eng</span>
</div>
<div class="job">
    <a href="https://example.com/careers/pm"><span class="title">PM</span></a>
    <span class="loc">Remote</span>
</div>
</body></html>
"""


class FakeSelectors:
    job_list = ".job"
    title = ".title"
    link = "a"
    location = ".loc"
    department = ".dept"


class FakeSelectorsNoOptional:
    job_list = ".job"
    title = ".title"
    link = "a"
    location = None
    department = None


@patch("app.scrapers.custom.requests.get")
def test_custom_scraper(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_HTML
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    scraper = CustomScraper(FakeSelectors())
    jobs = scraper.fetch_jobs("https://example.com/careers")

    assert len(jobs) == 2
    assert jobs[0].title == "Engineer"
    assert jobs[0].location == "NYC"
    assert jobs[0].department == "Eng"
    # Relative URL resolved
    assert str(jobs[0].url) == "https://example.com/careers/engineer"
    # Absolute URL preserved
    assert str(jobs[1].url) == "https://example.com/careers/pm"


@patch("app.scrapers.custom.requests.get")
def test_custom_scraper_no_optional_selectors(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_HTML
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    scraper = CustomScraper(FakeSelectorsNoOptional())
    jobs = scraper.fetch_jobs("https://example.com/careers")

    assert len(jobs) == 2
    assert jobs[0].location is None
    assert jobs[0].department is None


# --- Factory Tests ---

def test_factory_ashby():
    assert isinstance(get_scraper("ashby"), AshbyScraper)


def test_factory_workday():
    assert isinstance(get_scraper("workday"), WorkdayScraper)


def test_factory_custom_with_selectors():
    scraper = get_scraper("custom", FakeSelectors())
    assert isinstance(scraper, CustomScraper)


def test_factory_custom_without_selectors():
    with pytest.raises(ValueError, match="selectors"):
        get_scraper("custom")


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported ATS provider"):
        get_scraper("unknown_ats")
