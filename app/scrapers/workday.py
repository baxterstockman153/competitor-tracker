import re

import requests

from app.schemas.job import NormalizedJob
from app.scrapers.base import BaseScraper


class WorkdayScraper(BaseScraper):
    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        # careers_url format: https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
        jobs: list[NormalizedJob] = []
        offset = 0
        limit = 20

        while True:
            body = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }
            response = requests.post(
                careers_url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            total = data.get("total", 0)
            postings = data.get("jobPostings", [])

            base_url = careers_url.rsplit("/wday/cxs/", 1)[0]

            for item in postings:
                external_path = item.get("externalPath", "")
                match = re.search(r"_(R\d+)$", external_path)
                external_id = match.group(1) if match else external_path

                bullet_fields = item.get("bulletFields", [])
                description = " | ".join(bullet_fields) if bullet_fields else ""

                jobs.append(
                    NormalizedJob(
                        external_id=external_id,
                        title=item.get("title", ""),
                        location=item.get("locationsText"),
                        department=None,
                        description=description,
                        url=f"{base_url}{external_path}",
                    )
                )

            offset += limit
            if offset >= total:
                break

        return jobs
