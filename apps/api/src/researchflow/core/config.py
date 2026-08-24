from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
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
    simulation_step_delay: float = Field(default=0.7, ge=0, le=10)

    workflow_mode: Literal["simulation", "llm"] = "simulation"
    llm_provider: str = Field(default="openai-compatible", min_length=1)
    llm_model: str = ""
    llm_api_key: SecretStr | None = None
    llm_base_url: AnyHttpUrl = AnyHttpUrl("https://api.openai.com/v1")
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        if self.workflow_mode == "llm" and not self.llm_model.strip():
            raise ValueError("LLM 模式必须设置 RESEARCHFLOW_LLM_MODEL")
        return self

    def ensure_runtime_directories(self) -> None:
        if self.database_url.startswith("sqlite") and "///" in self.database_url:
            database_path = self.database_url.split("///", maxsplit=1)[1]
            if database_path != ":memory:":
                Path(database_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
