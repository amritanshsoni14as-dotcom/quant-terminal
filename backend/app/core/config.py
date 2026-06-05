"""Application configuration (pydantic-settings, reads .env)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — defaults to local SQLite so the app runs with zero setup.
    # Swap to Postgres in prod by setting DATABASE_URL=postgresql+psycopg://...
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'rainmumbai.db').as_posix()}"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"

    # Primary location: Mumbai (Santacruz)
    PRIMARY_LAT: float = 19.0896
    PRIMARY_LON: float = 72.8656
    PRIMARY_CODE: str = "MUMBAI"
    PRIMARY_NAME: str = "Mumbai (Santacruz)"

    # Backfill window (years of history to pull)
    BACKFILL_YEARS: int = 25

    # Monsoon season (Jun 1 .. Sep 30)
    MONSOON_START_MONTH: int = 6
    MONSOON_START_DAY: int = 1
    MONSOON_END_MONTH: int = 9
    MONSOON_END_DAY: int = 30

    # Optional keys (later phases)
    NOAA_TOKEN: str = ""
    COPERNICUS_CDS_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # AI engine for the Copilot / Alt-Data modules. Provider precedence:
    #   Groq (free cloud) > Anthropic > local Ollama.
    GROQ_API_KEY: str = ""        # free key: https://console.groq.com/keys
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Commodity fundamentals (free keys — connectors stay dormant until set).
    EIA_API_KEY: str = ""        # https://www.eia.gov/opendata/register.php
    FRED_API_KEY: str = ""       # https://fredaccount.stlouisfed.org/apikeys
    USDA_API_KEY: str = ""       # https://quickstats.nass.usda.gov/api

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
