import json

import httpx
import pytest
from pydantic import ValidationError

from researchflow.core.config import Settings
from researchflow.integrations.llm.openai_compatible import OpenAICompatibleLLMClient


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
                                            "search_query": "code generation task evaluation",
                                        },
                                        {
                                            "question": "哪些学术基准具有代表性？",
                                            "rationale": "需要选择可复现且被广泛使用的基准。",
                                            "search_query": "code generation benchmark dataset",
                                        },
                                        {
                                            "question": "如何评估真实开发者体验？",
                                            "rationale": "离线指标无法覆盖完整的使用体验。",
                                            "search_query": (
                                                "developer experience AI coding assistant"
                                            ),
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
        Settings(_env_file=None, workflow_mode="research")

    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_base_url="not-a-url")

    settings = Settings(
        _env_file=None,
        workflow_mode="research",
        llm_model="local-model",
        llm_api_key=None,
    )
    assert settings.llm_api_key is None
