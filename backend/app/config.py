import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Dynamically locate backend/.env regardless of where uvicorn was started from
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
_ROOT_ENV_FILE = _BACKEND_DIR.parent / ".env"


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # LLM Configuration (OpenAI / Gemini)
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"

    # External APIs
    PAGESPEED_API_KEY: Optional[str] = None
    GOOGLE_PAGESPEED_API_KEY: Optional[str] = None
    GOOGLE_PLACES_API_KEY: Optional[str] = None

    @property
    def openai_key(self) -> Optional[str]:
        return self.OPENAI_API_KEY or self.LLM_API_KEY

    @property
    def openai_model(self) -> str:
        return self.OPENAI_MODEL or self.LLM_MODEL or "gpt-4o-mini"

    @property
    def pagespeed_key(self) -> Optional[str]:
        return self.PAGESPEED_API_KEY or self.GOOGLE_PAGESPEED_API_KEY

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_FILE), str(_ROOT_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

