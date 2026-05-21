from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SelectorsConfig(BaseModel):
    job_list: str
    title: str
    link: str
    location: str | None = None
    department: str | None = None


class CompanyConfig(BaseModel):
    name: str
    careers_url: str
    ats_provider: str
    selectors: SelectorsConfig | None = None


class AppConfig(BaseModel):
    companies: list[CompanyConfig] = Field(default_factory=list)


def load_config(path: str | Path = "competitors.yaml") -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return AppConfig.model_validate(raw)
