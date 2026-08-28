import pytest
from pydantic import ValidationError

from researchflow.core.config import Settings


@pytest.mark.parametrize("removed_mode", ["llm", "langgraph"])
def test_removed_workflow_modes_are_rejected(removed_mode: str) -> None:
    with pytest.raises(ValidationError, match="workflow_mode"):
        Settings(_env_file=None, workflow_mode=removed_mode)


def test_production_rejects_local_cors_and_non_research_workflow() -> None:
    with pytest.raises(ValidationError, match="生产环境必须使用 research"):
        Settings(_env_file=None, environment="production", workflow_mode="simulation")

    with pytest.raises(ValidationError, match="公开前端 CORS Origin"):
        Settings(
            _env_file=None,
            environment="production",
            workflow_mode="research",
            llm_model="model",
            demo_access_code="long-demo-secret",
        )


def test_production_rejects_short_demo_access_code() -> None:
    with pytest.raises(ValidationError, match="至少 12 个字符"):
        Settings(
            _env_file=None,
            environment="production",
            workflow_mode="research",
            llm_model="model",
            cors_origins=("https://demo.example.com",),
            demo_access_code="too-short",
        )


def test_production_accepts_explicit_public_origin() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        workflow_mode="research",
        llm_model="model",
        cors_origins=("https://demo.example.com",),
        demo_access_code="long-demo-secret",
    )
    assert settings.environment == "production"
