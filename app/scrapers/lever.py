import requests
from bs4 import BeautifulSoup

from app.schemas.job import NormalizedJob
from app.scrapers.base import BaseScraper


class LeverScraper(BaseScraper):
    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        response = requests.get(careers_url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        jobs: list[NormalizedJob] = []
        for item in payload:
            description_html = item.get("descriptionPlain") or item.get("description", "")
            description_text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)

            jobs.append(
                NormalizedJob(
                    external_id=item.get("id", ""),
                    title=item.get("text", ""),
                    location=(item.get("categories") or {}).get("location"),
                    department=(item.get("categories") or {}).get("team"),
                    description=description_text,
                    url=item.get("hostedUrl", careers_url),
                )
            )
        return jobs
