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
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    simulation_step_delay: float = Field(default=0.7, ge=0, le=10)

    workflow_mode: Literal["simulation", "llm", "langgraph"] = "simulation"
    llm_provider: str = Field(default="openai-compatible", min_length=1)
    llm_model: str = ""
    llm_api_key: SecretStr | None = None
    llm_base_url: AnyHttpUrl = AnyHttpUrl("https://api.openai.com/v1")
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    web_search_provider: str = Field(default="exa", min_length=1, max_length=80)
    web_search_base_url: AnyHttpUrl = AnyHttpUrl("https://api.exa.ai")
    web_search_api_key: SecretStr | None = None
    web_search_result_limit: int = Field(default=3, ge=1, le=10)
    web_content_max_characters: int = Field(default=16000, ge=2000, le=50000)
    web_request_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    web_user_agent: str = Field(
        default="ResearchFlow/0.1 (portfolio research demo)",
        min_length=10,
        max_length=200,
    )

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        if self.workflow_mode in {"llm", "langgraph"} and not self.llm_model.strip():
            raise ValueError("LLM 或 LangGraph 模式必须设置 RESEARCHFLOW_LLM_MODEL")
        return self

    def ensure_runtime_directories(self) -> None:
        if self.database_url.startswith("sqlite") and "///" in self.database_url:
            database_path = self.database_url.split("///", maxsplit=1)[1]
            if database_path != ":memory:":
                Path(database_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
