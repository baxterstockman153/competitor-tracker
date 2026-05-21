import requests
from bs4 import BeautifulSoup

from app.schemas.job import NormalizedJob
from app.scrapers.base import BaseScraper


class AshbyScraper(BaseScraper):
    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        response = requests.get(careers_url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        jobs: list[NormalizedJob] = []
        for item in payload.get("jobs", []):
            description = item.get("descriptionPlain") or ""
            if not description:
                html = item.get("descriptionHtml", "")
                description = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

            jobs.append(
                NormalizedJob(
                    external_id=str(item["id"]),
                    title=item.get("title", ""),
                    location=item.get("location"),
                    department=item.get("department"),
                    description=description,
                    url=item.get("jobUrl", careers_url),
                )
            )
        return jobs
