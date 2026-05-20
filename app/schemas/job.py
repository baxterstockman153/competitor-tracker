from pydantic import BaseModel, HttpUrl


class NormalizedJob(BaseModel):
    external_id: str
    title: str
    location: str | None = None
    department: str | None = None
    description: str
    url: HttpUrl
