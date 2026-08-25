from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from researchflow.domain.research import (
    Evidence,
    ResearchEvent,
    ResearchMaterials,
    ResearchPlan,
    ResearchQuestion,
    ResearchRun,
    ResearchRunStatus,
    ResearchStage,
    ResearchTask,
    ResearchTaskStatus,
    Source,
)


class CreateResearchRunRequest(BaseModel):
    goal: str = Field(max_length=4000)

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = " ".join(value.split())
        if len(normalized) < 10:
            raise PydanticCustomError("goal_too_short", "研究目标至少需要 10 个字符")
        return normalized


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
    search_query: str

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


class ResearchEventResponse(BaseModel):
    sequence: int
    run_id: UUID
    type: str
    stage: ResearchStage | None
    message: str
    progress: int | None
    created_at: datetime
    payload: dict[str, object]

    @classmethod
    def from_domain(cls, event: ResearchEvent) -> "ResearchEventResponse":
        return cls(
            sequence=event.sequence,
            run_id=event.run_id,
            type=event.type,
            stage=event.stage,
            message=event.message,
            progress=event.progress,
            created_at=event.created_at,
            payload=event.payload or {},
        )


class ResearchEventListResponse(BaseModel):
    items: list[ResearchEventResponse]


class ResearchTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: UUID
    question_id: str
    query: str
    status: ResearchTaskStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, task: ResearchTask) -> "ResearchTaskResponse":
        return cls.model_validate(task)


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: UUID
    task_id: str
    title: str
    url: str
    snippet: str
    retrieved_at: datetime

    @classmethod
    def from_domain(cls, source: Source) -> "SourceResponse":
        return cls.model_validate(source)


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: UUID
    task_id: str
    question_id: str
    source_id: str
    excerpt: str
    summary: str
    created_at: datetime

    @classmethod
    def from_domain(cls, evidence: Evidence) -> "EvidenceResponse":
        return cls.model_validate(evidence)


class ResearchMaterialsResponse(BaseModel):
    run_id: UUID
    tasks: list[ResearchTaskResponse]
    sources: list[SourceResponse]
    evidence: list[EvidenceResponse]

    @classmethod
    def from_domain(cls, materials: ResearchMaterials) -> "ResearchMaterialsResponse":
        return cls(
            run_id=materials.run_id,
            tasks=[ResearchTaskResponse.from_domain(task) for task in materials.tasks],
            sources=[SourceResponse.from_domain(source) for source in materials.sources],
            evidence=[EvidenceResponse.from_domain(item) for item in materials.evidence],
        )
