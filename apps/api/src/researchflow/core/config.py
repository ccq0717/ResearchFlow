from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RESEARCHFLOW_",
        extra="ignore",
    )

    app_name: str = "ResearchFlow API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./var/researchflow.db"
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    simulation_step_delay: float = 0.7

    def ensure_runtime_directories(self) -> None:
        if self.database_url.startswith("sqlite") and "///" in self.database_url:
            database_path = self.database_url.split("///", maxsplit=1)[1]
            if database_path != ":memory:":
                Path(database_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
