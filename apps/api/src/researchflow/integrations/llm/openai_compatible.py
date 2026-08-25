import json
from time import perf_counter
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from researchflow.integrations.llm.base import (
    EvidenceDraft,
    LLMClientError,
    LLMEvidenceResult,
    LLMPlanResult,
    LLMReportResult,
    LLMUsage,
    ResearchDocumentInput,
    ResearchPlanDraft,
    ResearchQuestionDraft,
)


class _QuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=300)
    rationale: str = Field(min_length=5, max_length=500)
    search_query: str = Field(min_length=3, max_length=200)


class _PlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=10, max_length=1000)
    questions: list[_QuestionOutput] = Field(min_length=3, max_length=8)
    deliverables: list[str] = Field(min_length=1, max_length=8)


class _EvidenceItemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=80)
    question_id: str = Field(min_length=1, max_length=80)
    excerpt: str = Field(min_length=10, max_length=800)
    summary: str = Field(min_length=10, max_length=500)


class _EvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[_EvidenceItemOutput] = Field(min_length=1, max_length=24)


class _ReportOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_markdown: str = Field(min_length=100, max_length=20000)


OutputT = TypeVar("OutputT", bound=BaseModel)


class OpenAICompatibleLLMClient:
    """通过 Chat Completions + JSON Schema 完成研究模型操作。"""

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
        output, usage, duration_ms = await self._request_structured(
            system_prompt=(
                "你是 ResearchFlow 的研究规划器。请把用户目标拆成可检索、"
                "可验证的研究问题，并给出最终交付物。每个研究问题还要提供一条简洁的"
                "英文 search_query，供 Stack Overflow 技术检索使用。不要捏造资料或结论。"
            ),
            user_prompt=f"研究目标：{goal}",
            output_type=_PlanOutput,
            schema_name="research_plan",
            invalid_message="模型返回的数据格式不符合研究计划要求",
        )
        return LLMPlanResult(
            plan=ResearchPlanDraft(
                summary=output.summary,
                questions=tuple(
                    ResearchQuestionDraft(
                        question=question.question,
                        rationale=question.rationale,
                        search_query=question.search_query,
                    )
                    for question in output.questions
                ),
                deliverables=tuple(output.deliverables),
            ),
            provider=self._provider,
            model=self._model,
            usage=usage,
            duration_ms=duration_ms,
        )

    async def extract_evidence(
        self,
        goal: str,
        questions: tuple[ResearchQuestionDraft, ...],
        documents: tuple[ResearchDocumentInput, ...],
    ) -> LLMEvidenceResult:
        question_text = "\n".join(
            f"q{index}: {question.question}" for index, question in enumerate(questions, start=1)
        )
        document_text = "\n\n".join(
            (
                f"SOURCE {document.source_id}\n"
                f"标题：{document.title}\n网址：{document.url}\n正文：{document.content}"
            )
            for document in documents
        )
        output, usage, duration_ms = await self._request_structured(
            system_prompt=(
                "你是 ResearchFlow 的证据提取器。只从提供的网页正文提取证据。"
                "每条证据必须引用现有 source_id 和 question_id；excerpt 必须是正文中的短原文，"
                "summary 说明它怎样帮助回答问题。不要使用外部知识或编造原文。"
            ),
            user_prompt=(
                f"研究目标：{goal}\n\n研究问题：\n{question_text}\n\n网页资料：\n{document_text}"
            ),
            output_type=_EvidenceOutput,
            schema_name="research_evidence",
            invalid_message="模型返回的数据格式不符合研究证据要求",
        )
        allowed_sources = {document.source_id for document in documents}
        allowed_questions = {f"q{index}" for index in range(1, len(questions) + 1)}
        evidence = tuple(
            EvidenceDraft(
                source_id=item.source_id,
                question_id=item.question_id,
                excerpt=item.excerpt,
                summary=item.summary,
            )
            for item in output.evidence
            if item.source_id in allowed_sources and item.question_id in allowed_questions
        )
        if not evidence:
            raise LLMClientError(
                "LLM_INVALID_RESPONSE",
                "模型没有返回可关联到研究问题和来源的证据",
            )
        return LLMEvidenceResult(evidence=evidence, usage=usage, duration_ms=duration_ms)

    async def write_research_report(
        self,
        goal: str,
        plan: ResearchPlanDraft,
        evidence: tuple[EvidenceDraft, ...],
        documents: tuple[ResearchDocumentInput, ...],
    ) -> LLMReportResult:
        sources = "\n".join(
            f"{document.source_id}: [{document.title}]({document.url})" for document in documents
        )
        evidence_text = "\n".join(
            (f"- {item.question_id} / {item.source_id}: {item.summary}\n  原文：{item.excerpt}")
            for item in evidence
        )
        output, usage, duration_ms = await self._request_structured(
            system_prompt=(
                "你是 ResearchFlow 的报告撰写器。只能使用给定证据形成结论。"
                "用中文 Markdown 写一份结构化短报告；关键结论旁必须包含给定来源的可点击链接。"
                "明确说明证据不足之处，不要添加资料中没有的事实。"
            ),
            user_prompt=(
                f"研究目标：{goal}\n\n计划摘要：{plan.summary}\n"
                f"预期交付物：{list(plan.deliverables)}\n\n来源：\n{sources}\n\n证据：\n{evidence_text}"
            ),
            output_type=_ReportOutput,
            schema_name="research_report",
            invalid_message="模型返回的数据格式不符合研究报告要求",
        )
        return LLMReportResult(
            report_markdown=output.report_markdown,
            usage=usage,
            duration_ms=duration_ms,
        )

    async def _request_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[OutputT],
        schema_name: str,
        invalid_message: str,
    ) -> tuple[OutputT, LLMUsage, int]:
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
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": schema_name,
                                "strict": True,
                                "schema": output_type.model_json_schema(),
                            },
                        },
                    },
                )
                response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content must be a JSON string")
            output = output_type.model_validate_json(content)
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
            raise LLMClientError("LLM_INVALID_RESPONSE", invalid_message) from error

        return output, usage, max(1, round((perf_counter() - started) * 1000))

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
