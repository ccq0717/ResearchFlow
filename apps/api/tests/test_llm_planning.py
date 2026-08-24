import asyncio
import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from researchflow.app_factory import create_app
from researchflow.core.config import Settings
from researchflow.integrations.llm.base import LLMClientError, LLMPlanResult
from researchflow.integrations.llm.fake import FakeLLMClient
from researchflow.integrations.llm.openai_compatible import OpenAICompatibleLLMClient


class FailingLLMClient:
    async def create_research_plan(self, goal: str) -> LLMPlanResult:
        raise LLMClientError("LLM_HTTP_ERROR", "模型服务暂时不可用")


async def test_llm_workflow_generates_and_persists_plan(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'llm.db').as_posix()}",
            workflow_mode="llm",
            llm_model="test-model",
            simulation_step_delay=0,
        ),
        llm_client=FakeLLMClient(),
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "设计 AI 代码生成工具的工业界与学术界综合评测方案"},
            )
            assert created.status_code == 201
            run_id = created.json()["id"]

            detail = created
            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)

            assert detail.json()["status"] == "completed"
            assert "M1 演示结果" in detail.json()["report_markdown"]

            plan_response = await client.get(f"/api/research-runs/{run_id}/plan")
            assert plan_response.status_code == 200
            plan = plan_response.json()["plan"]
            assert plan["provider"] == "fake"
            assert plan["model"] == "fake-research-planner"
            assert len(plan["questions"]) == 3
            assert plan["questions"][0]["id"] == "q1"
            assert plan["total_tokens"] == 128


async def test_openai_compatible_adapter_parses_structured_output() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-secret"
        body = json.loads(request.content)
        assert body["model"] == "compatible-model"
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        schema = body["response_format"]["json_schema"]["schema"]
        assert schema["additionalProperties"] is False
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "建立覆盖质量、效率和安全性的综合评测框架。",
                                    "questions": [
                                        {
                                            "question": "应该评测哪些代码生成任务类型？",
                                            "rationale": "任务边界决定数据集和指标选择。",
                                        },
                                        {
                                            "question": "哪些学术基准具有代表性？",
                                            "rationale": "需要选择可复现且被广泛使用的基准。",
                                        },
                                        {
                                            "question": "如何评估真实开发者体验？",
                                            "rationale": "离线指标无法覆盖完整的使用体验。",
                                        },
                                    ],
                                    "deliverables": ["评测指标体系", "实验执行方案"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                    "total_tokens": 300,
                },
            },
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example/v1/",
        model="compatible-model",
        api_key="test-secret",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    result = await client.create_research_plan("设计 AI 代码生成工具评测方案")

    assert result.plan.summary.startswith("建立覆盖")
    assert len(result.plan.questions) == 3
    assert result.usage.total_tokens == 300
    assert result.duration_ms >= 1


def test_llm_settings_validate_required_model_and_base_url() -> None:
    with pytest.raises(ValidationError, match="RESEARCHFLOW_LLM_MODEL"):
        Settings(_env_file=None, workflow_mode="llm")

    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_base_url="not-a-url")

    settings = Settings(
        _env_file=None,
        workflow_mode="llm",
        llm_model="local-model",
        llm_api_key=None,
    )
    assert settings.llm_api_key is None


async def test_llm_failure_is_persisted_without_internal_details(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'failure.db').as_posix()}",
            workflow_mode="llm",
            llm_model="test-model",
            simulation_step_delay=0,
        ),
        llm_client=FailingLLMClient(),
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "设计一个能够安全处理模型错误的研究计划流程"},
            )
            run_id = created.json()["id"]

            detail = created
            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "failed":
                    break
                await asyncio.sleep(0.01)

            payload = detail.json()
            assert payload["status"] == "failed"
            assert payload["error_code"] == "LLM_HTTP_ERROR"
            assert payload["error_message"] == "模型服务暂时不可用"
            assert (await client.get(f"/api/research-runs/{run_id}/plan")).json()["plan"] is None
