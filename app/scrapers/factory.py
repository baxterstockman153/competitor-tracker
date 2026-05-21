from __future__ import annotations

from typing import TYPE_CHECKING

from app.scrapers.base import BaseScraper
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.lever import LeverScraper
from app.scrapers.ashby import AshbyScraper
from app.scrapers.workday import WorkdayScraper
from app.scrapers.custom import CustomScraper

if TYPE_CHECKING:
    from app.config import SelectorsConfig


def get_scraper(provider: str, selectors: SelectorsConfig | None = None) -> BaseScraper:
    normalized = provider.strip().lower()
    if normalized == "greenhouse":
        return GreenhouseScraper()
    if normalized == "lever":
        return LeverScraper()
    if normalized == "ashby":
        return AshbyScraper()
    if normalized == "workday":
        return WorkdayScraper()
    if normalized == "custom":
        if selectors is None:
            raise ValueError("Custom scraper requires 'selectors' configuration")
        return CustomScraper(selectors)
    raise ValueError(f"Unsupported ATS provider: {provider}")
