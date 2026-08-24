from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from researchflow.domain.research import (
    ResearchPlan,
    ResearchQuestion,
    ResearchRun,
    ResearchRunStatus,
    ResearchStage,
)


class CreateResearchRunRequest(BaseModel):
    goal: str = Field(min_length=10, max_length=4000)


class ResearchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    title: str
    status: ResearchRunStatus
    current_stage: ResearchStage | None
    progress: int
    report_markdown: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_domain(cls, run: ResearchRun) -> "ResearchRunResponse":
        return cls.model_validate(run)


class ResearchRunListResponse(BaseModel):
    items: list[ResearchRunResponse]


class ResearchQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    rationale: str

    @classmethod
    def from_domain(cls, question: ResearchQuestion) -> "ResearchQuestionResponse":
        return cls.model_validate(question)


class ResearchPlanResponse(BaseModel):
    run_id: UUID
    summary: str
    questions: list[ResearchQuestionResponse]
    deliverables: list[str]
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    duration_ms: int
    created_at: datetime

    @classmethod
    def from_domain(cls, plan: ResearchPlan) -> "ResearchPlanResponse":
        return cls(
            run_id=plan.run_id,
            summary=plan.summary,
            questions=[
                ResearchQuestionResponse.from_domain(question) for question in plan.questions
            ],
            deliverables=list(plan.deliverables),
            provider=plan.provider,
            model=plan.model,
            input_tokens=plan.input_tokens,
            output_tokens=plan.output_tokens,
            total_tokens=plan.total_tokens,
            duration_ms=plan.duration_ms,
            created_at=plan.created_at,
        )


class ResearchPlanEnvelope(BaseModel):
    plan: ResearchPlanResponse | None
