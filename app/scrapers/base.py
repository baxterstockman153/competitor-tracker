from abc import ABC, abstractmethod

from app.schemas.job import NormalizedJob


class BaseScraper(ABC):
    @abstractmethod
    def fetch_jobs(self, careers_url: str) -> list[NormalizedJob]:
        raise NotImplementedError
