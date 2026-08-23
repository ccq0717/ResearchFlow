import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from researchflow.domain.research import ResearchRun, ResearchRunStatus
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.simulated import SimulatedResearchWorkflow


class ResearchRunApplication:
    def __init__(
        self,
        repository: SqliteResearchRepository,
        workflow: SimulatedResearchWorkflow,
    ) -> None:
        self.repository = repository
        self.workflow = workflow
        self._tasks: set[asyncio.Task[None]] = set()

    async def create_run(self, goal: str) -> ResearchRun:
        now = datetime.now(UTC)
        normalized_goal = " ".join(goal.split())
        run = ResearchRun(
            id=uuid4(),
            goal=normalized_goal,
            title=self._title_from_goal(normalized_goal),
            status=ResearchRunStatus.QUEUED,
            current_stage=None,
            progress=0,
            report_markdown=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
        )
        await self.repository.create(run)
        await self.repository.append_event(
            run.id,
            event_type="run.queued",
            message="研究任务已创建，等待执行",
            progress=0,
        )
        task = asyncio.create_task(self.workflow.execute(run.id, run.goal))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run

    @staticmethod
    def _title_from_goal(goal: str) -> str:
        return goal if len(goal) <= 60 else f"{goal[:57]}..."

    async def get_run(self, run_id: UUID) -> ResearchRun | None:
        return await self.repository.get(run_id)

    async def list_runs(self) -> list[ResearchRun]:
        return await self.repository.list_runs()
