from pydantic import BaseModel, HttpUrl


class ParseJobUrlRequest(BaseModel):
    url: HttpUrl


class ParseJobUrlResponse(BaseModel):
    title: str
    company: str
    description: str
    location: str
    location_province: str
    source_url: str
