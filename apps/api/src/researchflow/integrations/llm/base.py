from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResearchQuestionDraft:
    question: str
    rationale: str


@dataclass(frozen=True, slots=True)
class ResearchPlanDraft:
    summary: str
    questions: tuple[ResearchQuestionDraft, ...]
    deliverables: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMPlanResult:
    plan: ResearchPlanDraft
    provider: str
    model: str
    usage: LLMUsage
    duration_ms: int


class LLMClientError(Exception):
    """可安全展示给用户的模型服务错误。"""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class LLMClient(Protocol):
    """模型模块的深接口：调用方不需要了解提示词、HTTP 或 JSON 解析。"""

    async def create_research_plan(self, goal: str) -> LLMPlanResult: ...
