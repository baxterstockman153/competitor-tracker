from app.scrapers.base import BaseScraper
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.lever import LeverScraper


def get_scraper(provider: str) -> BaseScraper:
    normalized = provider.strip().lower()
    if normalized == "greenhouse":
        return GreenhouseScraper()
    if normalized == "lever":
        return LeverScraper()
    raise ValueError(f"Unsupported ATS provider: {provider}")
