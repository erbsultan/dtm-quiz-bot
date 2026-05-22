from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    questions_file: str = Field(default="data/questions.example.json", alias="QUESTIONS_FILE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int] | None) -> list[int]:
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return value
        return [int(item.strip()) for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
