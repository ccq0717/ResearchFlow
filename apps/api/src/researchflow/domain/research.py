from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ResearchRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED}


class ResearchStage(StrEnum):
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    ANALYZING = "analyzing"
    WRITING = "writing"
    FINALIZING = "finalizing"


class ResearchTaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(StrEnum):
    ACADEMIC = "academic"
    OFFICIAL = "official"
    INDUSTRY = "industry"
    COMMUNITY = "community"
    OTHER = "other"


class SourceOrigin(StrEnum):
    WEB = "web"
    LOCAL = "local"


@dataclass(frozen=True, slots=True)
class ResearchRun:
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


@dataclass(frozen=True, slots=True)
class ResearchEvent:
    sequence: int
    run_id: UUID
    type: str
    stage: ResearchStage | None
    message: str
    progress: int | None
    payload: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ResearchEventDraft:
    type: str
    message: str
    stage: ResearchStage | None = None
    progress: int | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ResearchRunOutcome:
    status: ResearchRunStatus
    progress: int | None
    stage: ResearchStage | None
    report_markdown: str | None
    error_code: str | None
    error_message: str | None
    events: tuple[ResearchEventDraft, ...]


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    id: str
    question: str
    rationale: str
    search_query: str


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    run_id: UUID
    summary: str
    questions: tuple[ResearchQuestion, ...]
    deliverables: tuple[str, ...]
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    duration_ms: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ResearchTask:
    id: str
    run_id: UUID
    question_id: str
    query: str
    status: ResearchTaskStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    run_id: UUID
    task_id: str
    title: str
    url: str | None
    snippet: str
    retrieved_at: datetime
    source_type: SourceType = SourceType.OTHER
    author: str | None = None
    published_at: datetime | None = None
    publisher: str | None = None
    origin: SourceOrigin = SourceOrigin.WEB
    knowledge_document_id: UUID | None = None
    locator: str | None = None


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    run_id: UUID
    task_id: str
    question_id: str
    source_id: str
    excerpt: str
    summary: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Claim:
    id: str
    run_id: UUID
    question_id: str
    text: str
    evidence_ids: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CitationAudit:
    claim_count: int
    supported_claim_count: int
    coverage_percent: int
    unsupported_claim_ids: tuple[str, ...]
    source_type_counts: dict[SourceType, int]


@dataclass(frozen=True, slots=True)
class ResearchMaterials:
    run_id: UUID
    tasks: tuple[ResearchTask, ...]
    sources: tuple[Source, ...]
    evidence: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    citation_audit: CitationAudit
