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
    knowledge_upload_directory: Path = Path("./var/uploads")
    knowledge_max_document_bytes: int = Field(
        default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024
    )
    knowledge_max_document_count: int = Field(default=50, ge=1, le=500)
    knowledge_max_selection_count: int = Field(default=10, ge=1, le=50)
    knowledge_chunk_size: int = Field(default=1200, ge=300, le=4000)
    knowledge_max_extracted_characters: int = Field(
        default=2_000_000,
        ge=10_000,
        le=10_000_000,
    )
    knowledge_max_pdf_pages: int = Field(default=200, ge=1, le=1000)
    knowledge_max_pdf_page_stream_bytes: int = Field(
        default=5 * 1024 * 1024,
        ge=64 * 1024,
        le=50 * 1024 * 1024,
    )
    knowledge_results_per_question: int = Field(default=2, ge=1, le=10)
    embedding_provider: str = Field(default="gemini", min_length=1, max_length=80)
    embedding_model: str = ""
    embedding_api_key: SecretStr | None = None
    embedding_base_url: AnyHttpUrl = AnyHttpUrl("https://generativelanguage.googleapis.com/v1beta")
    embedding_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    embedding_dimensions: int | None = Field(default=None, ge=1, le=65536)

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
        self.knowledge_upload_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
