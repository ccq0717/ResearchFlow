from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from researchflow.domain.research import ResearchRun, ResearchRunStatus, ResearchStage


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
