import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from researchflow.domain.research import (
    ResearchEventDraft,
    ResearchPlan,
    ResearchRun,
    ResearchRunOutcome,
    ResearchRunStatus,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.base import ResearchWorkflow

logger = logging.getLogger(__name__)


class ResearchRunApplication:
    def __init__(
        self,
        repository: SqliteResearchRepository,
        workflow: ResearchWorkflow,
    ) -> None:
        self.repository = repository
        self.workflow = workflow
        self._tasks: dict[asyncio.Task[None], UUID] = {}

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
        task = asyncio.create_task(
            self.workflow.execute(run.id, run.goal),
            name=f"research-run-{run.id}",
        )
        self._tasks[task] = run.id
        task.add_done_callback(self._on_task_done)
        return run

    async def recover_interrupted_runs(self) -> None:
        for run in await self.repository.list_runs():
            if not run.status.is_terminal:
                await self._mark_interrupted(
                    run.id,
                    "检测到上次服务退出时未完成的研究任务，已将其标记为失败",
                )

    async def shutdown(self) -> None:
        active = tuple(self._tasks.items())
        for task, _ in active:
            task.cancel()
        if active:
            await asyncio.gather(
                *(task for task, _ in active),
                return_exceptions=True,
            )
        for run_id in {run_id for _, run_id in active}:
            run = await self.repository.get(run_id)
            if run is not None and not run.status.is_terminal:
                await self._mark_interrupted(
                    run_id,
                    "后端服务停止，研究任务已中断",
                )

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        run_id = self._tasks.pop(task, None)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "研究后台任务异常结束，run_id=%s",
                run_id,
                exc_info=(type(error), error, error.__traceback__),
            )

    async def _mark_interrupted(self, run_id: UUID, message: str) -> None:
        await self.repository.finalize(
            run_id,
            ResearchRunOutcome(
                status=ResearchRunStatus.FAILED,
                progress=None,
                stage=None,
                report_markdown=None,
                error_code="RUN_INTERRUPTED",
                error_message=message,
                events=(
                    ResearchEventDraft(
                        type="run.failed",
                        message=message,
                        payload={"code": "RUN_INTERRUPTED"},
                    ),
                ),
            ),
        )

    @staticmethod
    def _title_from_goal(goal: str) -> str:
        return goal if len(goal) <= 60 else f"{goal[:57]}..."

    async def get_run(self, run_id: UUID) -> ResearchRun | None:
        return await self.repository.get(run_id)

    async def get_plan(self, run_id: UUID) -> ResearchPlan | None:
        return await self.repository.get_plan(run_id)

    async def list_runs(self) -> list[ResearchRun]:
        return await self.repository.list_runs()
