import json
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from researchflow.integrations.llm.base import (
    LLMClientError,
    LLMPlanResult,
    LLMUsage,
    ResearchPlanDraft,
    ResearchQuestionDraft,
)


class _QuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=300)
    rationale: str = Field(min_length=5, max_length=500)


class _PlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=10, max_length=1000)
    questions: list[_QuestionOutput] = Field(min_length=3, max_length=8)
    deliverables: list[str] = Field(min_length=1, max_length=8)


class OpenAICompatibleLLMClient:
    """通过 Chat Completions + JSON Schema 调用 OpenAI 兼容服务。"""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: float,
        provider: str = "openai-compatible",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._provider = provider
        self._transport = transport

    async def create_research_plan(self, goal: str) -> LLMPlanResult:
        started = perf_counter()
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers=headers,
                    json=self._request_body(goal),
                )
                response.raise_for_status()
            payload = response.json()
            output = self._parse_plan(payload)
            usage = self._parse_usage(payload)
        except httpx.TimeoutException as error:
            raise LLMClientError("LLM_TIMEOUT", "模型服务响应超时，请稍后重试") from error
        except httpx.HTTPStatusError as error:
            raise LLMClientError(
                "LLM_HTTP_ERROR",
                f"模型服务返回错误状态（HTTP {error.response.status_code}）",
            ) from error
        except httpx.RequestError as error:
            raise LLMClientError("LLM_CONNECTION_ERROR", "无法连接模型服务") from error
        except (
            json.JSONDecodeError,
            IndexError,
            KeyError,
            TypeError,
            ValidationError,
        ) as error:
            raise LLMClientError(
                "LLM_INVALID_RESPONSE",
                "模型返回的数据格式不符合研究计划要求",
            ) from error

        return LLMPlanResult(
            plan=ResearchPlanDraft(
                summary=output.summary,
                questions=tuple(
                    ResearchQuestionDraft(
                        question=question.question,
                        rationale=question.rationale,
                    )
                    for question in output.questions
                ),
                deliverables=tuple(output.deliverables),
            ),
            provider=self._provider,
            model=self._model,
            usage=usage,
            duration_ms=max(1, round((perf_counter() - started) * 1000)),
        )

    def _request_body(self, goal: str) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 ResearchFlow 的研究规划器。请把用户目标拆成可检索、"
                        "可验证的研究问题，并给出最终交付物。不要捏造资料或结论。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"研究目标：{goal}",
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "research_plan",
                    "strict": True,
                    "schema": _PlanOutput.model_json_schema(),
                },
            },
        }

    @staticmethod
    def _parse_plan(payload: dict[str, Any]) -> _PlanOutput:
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("message.content must be a JSON string")
        return _PlanOutput.model_validate_json(content)

    @staticmethod
    def _parse_usage(payload: dict[str, Any]) -> LLMUsage:
        raw = payload.get("usage") or {}
        if not isinstance(raw, dict):
            raise TypeError("usage must be an object")
        return LLMUsage(
            input_tokens=raw.get("prompt_tokens"),
            output_tokens=raw.get("completion_tokens"),
            total_tokens=raw.get("total_tokens"),
        )
