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
    ResearchRunMetrics,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchTaskStatus,
    SourceOrigin,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.base import ResearchWorkflow, ResearchWorkflowUpdate

logger = logging.getLogger(__name__)


class ResearchRunApplicationError(Exception):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class ResearchRunApplication:
    def __init__(
        self,
        repository: SqliteResearchRepository,
        workflow: ResearchWorkflow,
        knowledge_library: KnowledgeLibrary,
        *,
        llm_input_cost_per_million_tokens: float | None = None,
        llm_output_cost_per_million_tokens: float | None = None,
        max_concurrent_runs: int = 2,
        max_runs_per_day: int = 20,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self._knowledge_library = knowledge_library
        self._tasks: dict[asyncio.Task[None], UUID] = {}
        self._lifecycle_lock = asyncio.Lock()
        self._create_lock = asyncio.Lock()
        self._llm_input_cost = llm_input_cost_per_million_tokens
        self._llm_output_cost = llm_output_cost_per_million_tokens
        self._max_concurrent_runs = max_concurrent_runs
        self._max_runs_per_day = max_runs_per_day

    async def create_run(
        self,
        goal: str,
        document_ids: tuple[UUID, ...] = (),
        *,
        retry_of: UUID | None = None,
        attempt: int = 1,
    ) -> ResearchRun:
        selected_document_ids = await self._knowledge_library.validate_selection(document_ids)
        async with self._create_lock:
            now = datetime.now(UTC)
            if sum(not task.done() for task in self._tasks) >= self._max_concurrent_runs:
                raise ResearchRunApplicationError(
                    "RUN_CAPACITY_REACHED", "当前研究任务已达并发上限，请稍后再试"
                )
            runs = await self._repository.list_runs(include_archived=True)
            if sum(run.created_at.date() == now.date() for run in runs) >= self._max_runs_per_day:
                raise ResearchRunApplicationError(
                    "DAILY_RUN_LIMIT_REACHED", "今日研究任务额度已用完，请明天再试"
                )
            return await self._create_run(
                goal,
                selected_document_ids,
                retry_of=retry_of,
                attempt=attempt,
                now=now,
            )

    async def _create_run(
        self,
        goal: str,
        selected_document_ids: tuple[UUID, ...],
        *,
        retry_of: UUID | None,
        attempt: int,
        now: datetime,
    ) -> ResearchRun:
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
            retry_of=retry_of,
            attempt=attempt,
        )
        await self._repository.create(run)
        await self._knowledge_library.link_run(run.id, selected_document_ids)
        await self._repository.append_event(
            run.id,
            event_type="run.queued",
            message=(
                f"研究任务第 {attempt} 次运行已创建，等待执行"
                if retry_of is not None
                else "研究任务已创建，等待执行"
            ),
            progress=0,
            payload={"retry_of": str(retry_of), "attempt": attempt}
            if retry_of is not None
            else None,
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
                await self._apply_workflow_update_safely(run_id, update)
        except Exception:
            logger.exception("研究工作流执行失败，run_id=%s", run_id)
            current = await self._repository.get(run_id)
            if current is not None and not current.status.is_terminal:
                await self._finalize_failed_run(
                    run_id,
                    code="WORKFLOW_FAILED",
                    message="研究工作流执行失败，请稍后重试",
                )

    async def _apply_workflow_update_safely(
        self,
        run_id: UUID,
        update: ResearchWorkflowUpdate,
    ) -> None:
        persistence = asyncio.create_task(self._apply_workflow_update(run_id, update))
        try:
            await asyncio.shield(persistence)
        except asyncio.CancelledError:
            await persistence
            raise

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
        async with self._lifecycle_lock:
            active = tuple(self._tasks.items())
            for task, _ in active:
                task.cancel()
            if active:
                await asyncio.gather(
                    *(task for task, _ in active),
                    return_exceptions=True,
                )

    async def cancel_run(self, run_id: UUID) -> ResearchRun:
        async with self._lifecycle_lock:
            run = await self._repository.get(run_id)
            if run is None:
                raise ResearchRunApplicationError("RUN_NOT_FOUND", "研究任务不存在")
            if run.status.is_terminal:
                raise ResearchRunApplicationError(
                    "RUN_NOT_CANCELLABLE",
                    "只有排队中或运行中的研究任务可以取消",
                )

            active_task = next(
                (task for task, active_run_id in self._tasks.items() if active_run_id == run_id),
                None,
            )
            if active_task is not None:
                active_task.cancel()
                await asyncio.gather(active_task, return_exceptions=True)

            current = await self._repository.get(run_id)
            if current is None:
                raise ResearchRunApplicationError("RUN_NOT_FOUND", "研究任务不存在")
            if current.status.is_terminal:
                raise ResearchRunApplicationError(
                    "RUN_NOT_CANCELLABLE",
                    "研究任务已在取消前结束",
                )
            return await self._repository.finalize(
                run_id,
                ResearchRunOutcome(
                    status=ResearchRunStatus.CANCELLED,
                    progress=None,
                    stage=None,
                    report_markdown=None,
                    error_code=None,
                    error_message=None,
                    events=(
                        ResearchEventDraft(
                            type="run.cancelled",
                            message="研究任务已由用户取消",
                        ),
                    ),
                ),
            )

    async def retry_run(self, run_id: UUID) -> ResearchRun:
        source = await self._require_run(run_id)
        if source.status is not ResearchRunStatus.FAILED:
            raise ResearchRunApplicationError("RUN_NOT_RETRYABLE", "只有失败的研究任务可以重试")
        if source.attempt >= 2:
            raise ResearchRunApplicationError(
                "RUN_RETRY_LIMIT_REACHED", "该研究任务已经达到一次重试上限"
            )
        document_ids = await self._knowledge_library.list_run_document_ids(run_id)
        retried = await self.create_run(
            source.goal,
            document_ids,
            retry_of=source.id,
            attempt=source.attempt + 1,
        )
        await self._repository.append_event(
            source.id,
            event_type="run.retry.created",
            message="已创建一次新的研究运行",
            payload={"run_id": str(retried.id), "attempt": retried.attempt},
        )
        return retried

    async def rename_run(self, run_id: UUID, title: str) -> ResearchRun:
        await self._require_run(run_id)
        return await self._repository.rename(run_id, title)

    async def archive_run(self, run_id: UUID, archived: bool) -> ResearchRun:
        run = await self._require_run(run_id)
        if not run.status.is_terminal:
            raise ResearchRunApplicationError("RUN_NOT_ARCHIVABLE", "只有已结束的研究任务可以归档")
        return await self._repository.set_archived(run_id, archived)

    async def delete_run(self, run_id: UUID) -> None:
        run = await self._require_run(run_id)
        if not run.status.is_terminal:
            raise ResearchRunApplicationError("RUN_NOT_DELETABLE", "只有已结束的研究任务可以删除")
        await self._repository.delete(run_id)

    async def _require_run(self, run_id: UUID) -> ResearchRun:
        run = await self._repository.get(run_id)
        if run is None:
            raise ResearchRunApplicationError("RUN_NOT_FOUND", "研究任务不存在")
        return run

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

    async def get_metrics(self, run_id: UUID) -> ResearchRunMetrics:
        run = await self._require_run(run_id)
        materials = await self._repository.get_materials(run_id)
        events = await self._repository.events_after(run_id, 0)
        llm_payloads = [
            event.payload
            for event in events
            if event.payload and event.payload.get("llm_call") is True
        ]

        def total(field: str) -> int | None:
            values = [
                value for payload in llm_payloads if isinstance((value := payload.get(field)), int)
            ]
            return sum(values) if values else None

        input_tokens = total("input_tokens")
        output_tokens = total("output_tokens")
        estimated_cost = None
        if (
            input_tokens is not None
            and output_tokens is not None
            and self._llm_input_cost is not None
            and self._llm_output_cost is not None
        ):
            estimated_cost = round(
                (input_tokens * self._llm_input_cost + output_tokens * self._llm_output_cost)
                / 1_000_000,
                6,
            )
        duration_ms = None
        if run.started_at is not None:
            end = run.completed_at or datetime.now(UTC)
            duration_ms = max(0, round((end - run.started_at).total_seconds() * 1000))
        return ResearchRunMetrics(
            duration_ms=duration_ms,
            llm_duration_ms=total("duration_ms") or 0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total("total_tokens"),
            estimated_llm_cost_usd=estimated_cost,
            task_count=len(materials.tasks),
            failed_task_count=sum(
                task.status is ResearchTaskStatus.FAILED for task in materials.tasks
            ),
            source_count=len(materials.sources),
            web_source_count=sum(source.origin is SourceOrigin.WEB for source in materials.sources),
            local_source_count=sum(
                source.origin is SourceOrigin.LOCAL for source in materials.sources
            ),
            evidence_count=len(materials.evidence),
            claim_count=len(materials.claims),
            citation_coverage_percent=materials.citation_audit.coverage_percent,
        )

    async def list_events(self, run_id: UUID) -> list[ResearchEvent]:
        return await self._repository.events_after(run_id, 0)

    async def events_after(self, run_id: UUID, sequence: int) -> list[ResearchEvent]:
        return await self._repository.events_after(run_id, sequence)

    async def list_runs(self, *, include_archived: bool = False) -> list[ResearchRun]:
        return await self._repository.list_runs(include_archived=include_archived)
