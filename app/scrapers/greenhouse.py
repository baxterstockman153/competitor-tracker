import requests

from app.schemas.job import NormalizedJob
from app.scrapers.base import BaseScraper


class GreenhouseScraper(BaseScraper):
    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        response = requests.get(careers_url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        jobs: list[NormalizedJob] = []
        for item in payload.get("jobs", []):
            jobs.append(
                NormalizedJob(
                    external_id=str(item["id"]),
                    title=item.get("title", ""),
                    location=(item.get("location") or {}).get("name"),
                    department=(item.get("departments") or [{}])[0].get("name"),
                    description=item.get("content", ""),
                    url=item.get("absolute_url", careers_url),
                )
            )
        return jobs
