import pytest
from pydantic import ValidationError

from researchflow.core.config import Settings


def test_production_rejects_local_cors_and_non_langgraph_workflow() -> None:
    with pytest.raises(ValidationError, match="生产环境必须使用 langgraph"):
        Settings(_env_file=None, environment="production", workflow_mode="simulation")

    with pytest.raises(ValidationError, match="公开前端 CORS Origin"):
        Settings(
            _env_file=None,
            environment="production",
            workflow_mode="langgraph",
            llm_model="model",
            demo_access_code="long-demo-secret",
        )


def test_production_rejects_short_demo_access_code() -> None:
    with pytest.raises(ValidationError, match="至少 12 个字符"):
        Settings(
            _env_file=None,
            environment="production",
            workflow_mode="langgraph",
            llm_model="model",
            cors_origins=("https://demo.example.com",),
            demo_access_code="too-short",
        )


def test_production_accepts_explicit_public_origin() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        workflow_mode="langgraph",
        llm_model="model",
        cors_origins=("https://demo.example.com",),
        demo_access_code="long-demo-secret",
    )
    assert settings.environment == "production"
