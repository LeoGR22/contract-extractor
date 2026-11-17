from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_model: str = "gemini-3.8-flash"
    thinking_level: str = "low"
    max_upload_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
