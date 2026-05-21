import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.schemas.job import NormalizedJob
from app.scrapers.base import BaseScraper


class CustomScraper(BaseScraper):
    def __init__(self, selectors):
        self.selectors = selectors

    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        response = requests.get(careers_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        jobs: list[NormalizedJob] = []
        elements = soup.select(self.selectors.job_list)

        for el in elements:
            title_el = el.select_one(self.selectors.title)
            title = title_el.get_text(strip=True) if title_el else ""

            link_el = el.select_one(self.selectors.link)
            href = link_el.get("href", "") if link_el else ""
            url = urljoin(careers_url, href) if href else careers_url

            location = None
            if self.selectors.location:
                loc_el = el.select_one(self.selectors.location)
                location = loc_el.get_text(strip=True) if loc_el else None

            department = None
            if self.selectors.department:
                dept_el = el.select_one(self.selectors.department)
                department = dept_el.get_text(strip=True) if dept_el else None

            external_id = href or hashlib.md5(title.encode()).hexdigest()

            jobs.append(
                NormalizedJob(
                    external_id=external_id,
                    title=title,
                    location=location,
                    department=department,
                    description=title,
                    url=url,
                )
            )
        return jobs
