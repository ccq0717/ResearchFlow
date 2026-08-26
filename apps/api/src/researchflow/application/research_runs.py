import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from researchflow.application.knowledge_library import KnowledgeLibrary
from researchflow.domain.research import (
    ResearchEvent,
    ResearchEventDraft,
    ResearchMaterials,
    ResearchPlan,
    ResearchRun,
    ResearchRunOutcome,
    ResearchRunStatus,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.base import ResearchWorkflow, ResearchWorkflowUpdate

logger = logging.getLogger(__name__)


class ResearchRunApplication:
    def __init__(
        self,
        repository: SqliteResearchRepository,
        workflow: ResearchWorkflow,
        knowledge_library: KnowledgeLibrary,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self._knowledge_library = knowledge_library
        self._tasks: dict[asyncio.Task[None], UUID] = {}

    async def create_run(
        self,
        goal: str,
        document_ids: tuple[UUID, ...] = (),
    ) -> ResearchRun:
        selected_document_ids = await self._knowledge_library.validate_selection(document_ids)
        now = datetime.now(UTC)
        run = ResearchRun(
            id=uuid4(),
            goal=goal,
            title=self._title_from_goal(goal),
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
        await self._repository.create(run)
        await self._knowledge_library.link_run(run.id, selected_document_ids)
        await self._repository.append_event(
            run.id,
            event_type="run.queued",
            message="研究任务已创建，等待执行",
            progress=0,
        )
        task = asyncio.create_task(
            self._execute_workflow(run.id, run.goal, selected_document_ids),
            name=f"research-run-{run.id}",
        )
        self._tasks[task] = run.id
        task.add_done_callback(self._on_task_done)
        return run

    async def _execute_workflow(
        self,
        run_id: UUID,
        goal: str,
        document_ids: tuple[UUID, ...],
    ) -> None:
        try:
            async for update in self._workflow.execute(run_id, goal, document_ids):
                await self._apply_workflow_update(run_id, update)
        except Exception:
            logger.exception("研究工作流执行失败，run_id=%s", run_id)
            current = await self._repository.get(run_id)
            if current is not None and not current.status.is_terminal:
                await self._finalize_failed_run(
                    run_id,
                    code="WORKFLOW_FAILED",
                    message="研究工作流执行失败，请稍后重试",
                )

    async def _apply_workflow_update(self, run_id: UUID, update: ResearchWorkflowUpdate) -> None:
        if update.outcome is not None:
            await self._repository.finalize(run_id, update.outcome)
            return

        if any(
            value is not None
            for value in (
                update.status,
                update.stage,
                update.progress,
                update.started_at,
            )
        ):
            await self._repository.update(
                run_id,
                status=update.status,
                stage=update.stage,
                progress=update.progress,
                started_at=update.started_at,
            )
        if update.plan is not None:
            await self._repository.save_plan(update.plan)
        if update.tasks or update.sources or update.evidence or update.claims:
            await self._repository.save_materials(
                tasks=update.tasks,
                sources=update.sources,
                evidence=update.evidence,
                claims=update.claims,
            )
        for event in update.events:
            await self._repository.append_event(
                run_id,
                event_type=event.type,
                stage=event.stage,
                message=event.message,
                progress=event.progress,
                payload=event.payload,
            )

    async def recover_interrupted_runs(self) -> None:
        for run in await self._repository.list_runs():
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
            run = await self._repository.get(run_id)
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
        await self._finalize_failed_run(run_id, code="RUN_INTERRUPTED", message=message)

    async def _finalize_failed_run(self, run_id: UUID, *, code: str, message: str) -> None:
        await self._repository.finalize(
            run_id,
            ResearchRunOutcome(
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
            ),
        )

    @staticmethod
    def _title_from_goal(goal: str) -> str:
        return goal if len(goal) <= 60 else f"{goal[:57]}..."

    async def get_run(self, run_id: UUID) -> ResearchRun | None:
        return await self._repository.get(run_id)

    async def get_plan(self, run_id: UUID) -> ResearchPlan | None:
        return await self._repository.get_plan(run_id)

    async def get_materials(self, run_id: UUID) -> ResearchMaterials:
        return await self._repository.get_materials(run_id)

    async def list_events(self, run_id: UUID) -> list[ResearchEvent]:
        return await self._repository.events_after(run_id, 0)

    async def events_after(self, run_id: UUID, sequence: int) -> list[ResearchEvent]:
        return await self._repository.events_after(run_id, sequence)

    async def list_runs(self) -> list[ResearchRun]:
        return await self._repository.list_runs()
