from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from researchflow.domain.research import (
    Claim,
    Evidence,
    ResearchEventDraft,
    ResearchPlan,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
    ResearchTask,
    Source,
)


@dataclass(frozen=True, slots=True)
class ResearchWorkflowUpdate:
    """工作流交给应用层持久化的一次领域更新。"""

    status: ResearchRunStatus | None = None
    stage: ResearchStage | None = None
    progress: int | None = None
    started_at: datetime | None = None
    plan: ResearchPlan | None = None
    tasks: tuple[ResearchTask, ...] = ()
    sources: tuple[Source, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    claims: tuple[Claim, ...] = ()
    events: tuple[ResearchEventDraft, ...] = ()
    outcome: ResearchRunOutcome | None = None

    def __post_init__(self) -> None:
        if self.outcome is not None and any(
            value is not None
            for value in (
                self.status,
                self.stage,
                self.progress,
                self.started_at,
                self.plan,
                self.tasks or None,
                self.sources or None,
                self.evidence or None,
                self.claims or None,
            )
        ):
            raise ValueError("终态更新不能同时包含普通状态或计划")
        if self.outcome is not None and self.events:
            raise ValueError("终态事件必须由 ResearchRunOutcome 携带")


class ResearchWorkflow(Protocol):
    """研究工作流对应用层暴露的最小接口。"""

    def execute(
        self,
        run_id: UUID,
        goal: str,
        document_ids: tuple[UUID, ...] = (),
    ) -> AsyncIterator[ResearchWorkflowUpdate]: ...


def workflow_started_update(message: str) -> ResearchWorkflowUpdate:
    return ResearchWorkflowUpdate(
        status=ResearchRunStatus.RUNNING,
        progress=2,
        started_at=datetime.now(UTC),
        events=(
            ResearchEventDraft(
                type="run.started",
                message=message,
                progress=2,
            ),
        ),
    )


def workflow_failure_update(code: str, message: str) -> ResearchWorkflowUpdate:
    return ResearchWorkflowUpdate(
        outcome=ResearchRunOutcome(
            status=ResearchRunStatus.FAILED,
            progress=None,
            stage=None,
            report_markdown=None,
            error_code=code,
            error_message=message,
            events=(
                ResearchEventDraft(
                    type="run.failed",
                    message=message,
                    payload={"code": code},
                ),
            ),
        )
    )
