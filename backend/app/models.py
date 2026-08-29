from pydantic import BaseModel, HttpUrl, field_validator
import re


class HealthResponse(BaseModel):
    status: str = "ok"
    message: str = "Website SEO & Visibility Analyser backend is running"


class AnalysisRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_and_normalize_url(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("URL cannot be empty")
        if not re.match(r"^https?://", cleaned, re.IGNORECASE):
            cleaned = f"https://{cleaned}"
        return cleaned


class AnalysisResponse(BaseModel):
    status: str = "connected"
    message: str = "Endpoint connected successfully. Full analysis engine will be activated in subsequent phases."
    target_url: str
