from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from researchflow.domain.knowledge import DocumentChunk, KnowledgeDocument, KnowledgeDocumentStatus
from researchflow.domain.research import (
    CitationAudit,
    Claim,
    Evidence,
    ResearchEvent,
    ResearchMaterials,
    ResearchPlan,
    ResearchQuestion,
    ResearchRun,
    ResearchRunMetrics,
    ResearchRunStatus,
    ResearchStage,
    ResearchTask,
    ResearchTaskStatus,
    Source,
    SourceOrigin,
    SourceType,
)


class CreateResearchRunRequest(BaseModel):
    goal: str = Field(max_length=4000)
    document_ids: tuple[UUID, ...] = Field(default=(), max_length=50)

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = " ".join(value.split())
        if len(normalized) < 10:
            raise PydanticCustomError("goal_too_short", "研究目标至少需要 10 个字符")
        return normalized


class RenameResearchRunRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class ArchiveResearchRunRequest(BaseModel):
    archived: bool = True


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
    archived: bool
    retry_of: UUID | None
    attempt: int

    @classmethod
    def from_domain(cls, run: ResearchRun) -> "ResearchRunResponse":
        return cls.model_validate(run)


class ResearchRunListResponse(BaseModel):
    items: list[ResearchRunResponse]


class ResearchRunMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    duration_ms: int | None
    llm_duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_llm_cost_usd: float | None
    task_count: int
    failed_task_count: int
    source_count: int
    web_source_count: int
    local_source_count: int
    evidence_count: int
    claim_count: int
    citation_coverage_percent: int

    @classmethod
    def from_domain(cls, metrics: ResearchRunMetrics) -> "ResearchRunMetricsResponse":
        return cls.model_validate(metrics)


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
    url: str | None
    snippet: str
    retrieved_at: datetime
    source_type: SourceType
    author: str | None
    published_at: datetime | None
    publisher: str | None
    origin: SourceOrigin
    knowledge_document_id: UUID | None
    locator: str | None

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


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: UUID
    question_id: str
    text: str
    evidence_ids: list[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, claim: Claim) -> "ClaimResponse":
        return cls(
            id=claim.id,
            run_id=claim.run_id,
            question_id=claim.question_id,
            text=claim.text,
            evidence_ids=list(claim.evidence_ids),
            created_at=claim.created_at,
        )


class CitationAuditResponse(BaseModel):
    claim_count: int
    supported_claim_count: int
    coverage_percent: int
    unsupported_claim_ids: list[str]
    source_type_counts: dict[SourceType, int]

    @classmethod
    def from_domain(cls, audit: CitationAudit) -> "CitationAuditResponse":
        return cls(
            claim_count=audit.claim_count,
            supported_claim_count=audit.supported_claim_count,
            coverage_percent=audit.coverage_percent,
            unsupported_claim_ids=list(audit.unsupported_claim_ids),
            source_type_counts=audit.source_type_counts,
        )


class ResearchMaterialsResponse(BaseModel):
    run_id: UUID
    tasks: list[ResearchTaskResponse]
    sources: list[SourceResponse]
    evidence: list[EvidenceResponse]
    claims: list[ClaimResponse]
    citation_audit: CitationAuditResponse

    @classmethod
    def from_domain(cls, materials: ResearchMaterials) -> "ResearchMaterialsResponse":
        return cls(
            run_id=materials.run_id,
            tasks=[ResearchTaskResponse.from_domain(task) for task in materials.tasks],
            sources=[SourceResponse.from_domain(source) for source in materials.sources],
            evidence=[EvidenceResponse.from_domain(item) for item in materials.evidence],
            claims=[ClaimResponse.from_domain(claim) for claim in materials.claims],
            citation_audit=CitationAuditResponse.from_domain(materials.citation_audit),
        )


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    status: KnowledgeDocumentStatus
    chunk_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: KnowledgeDocument) -> "KnowledgeDocumentResponse":
        return cls(
            id=document.id,
            original_filename=document.original_filename,
            media_type=document.media_type,
            size_bytes=document.size_bytes,
            status=document.status,
            chunk_count=document.chunk_count,
            error_code=document.error_code,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]


class DocumentChunkResponse(BaseModel):
    id: str
    document_id: UUID
    ordinal: int
    content: str
    locator: str
    page_number: int | None
    start_line: int | None
    end_line: int | None

    @classmethod
    def from_domain(cls, chunk: DocumentChunk) -> "DocumentChunkResponse":
        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            ordinal=chunk.ordinal,
            content=chunk.content,
            locator=chunk.locator,
            page_number=chunk.page_number,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
        )


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
