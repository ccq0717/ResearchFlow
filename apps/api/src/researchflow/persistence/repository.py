import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from researchflow.domain.research import (
    ResearchEvent,
    ResearchEventDraft,
    ResearchPlan,
    ResearchQuestion,
    ResearchRun,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
)
from researchflow.persistence.database import Base


class ResearchRunRow(Base):
    __tablename__ = "research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[ResearchRunStatus] = mapped_column(Enum(ResearchRunStatus))
    current_stage: Mapped[ResearchStage | None] = mapped_column(Enum(ResearchStage))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    report_markdown: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResearchPlanRow(Base):
    __tablename__ = "research_plans"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[str] = mapped_column(Text)
    questions: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    deliverables: Mapped[list[str]] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(160))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResearchEventRow(Base):
    __tablename__ = "research_events"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(80))
    stage: Mapped[ResearchStage | None] = mapped_column(Enum(ResearchStage))
    message: Mapped[str] = mapped_column(Text)
    progress: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SqliteResearchRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sessions = session_factory

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        session = self._sessions()
        try:
            yield session
        except asyncio.CancelledError:
            # SQLite 提交由工作线程执行。协程取消时必须等待回滚完成，
            # 否则后台连接可能继续持有写锁，阻塞关闭流程的终态写入。
            await asyncio.shield(session.rollback())
            raise
        finally:
            await asyncio.shield(session.close())

    async def create(self, run: ResearchRun) -> ResearchRun:
        async with self._session() as session:
            session.add(self._run_to_row(run))
            await session.commit()
        return run

    async def get(self, run_id: UUID) -> ResearchRun | None:
        async with self._session() as session:
            row = await session.get(ResearchRunRow, str(run_id))
            return self._row_to_run(row) if row else None

    async def list_runs(self) -> list[ResearchRun]:
        async with self._session() as session:
            result = await session.scalars(
                select(ResearchRunRow).order_by(ResearchRunRow.created_at.desc())
            )
            return [self._row_to_run(row) for row in result]

    async def update(
        self,
        run_id: UUID,
        *,
        status: ResearchRunStatus | None = None,
        stage: ResearchStage | None = None,
        progress: int | None = None,
        report_markdown: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> ResearchRun:
        async with self._session() as session:
            row = await session.get(ResearchRunRow, str(run_id))
            if row is None:
                raise KeyError(str(run_id))
            if status is not None:
                row.status = status
            if stage is not None:
                row.current_stage = stage
            if progress is not None:
                row.progress = progress
            if report_markdown is not None:
                row.report_markdown = report_markdown
            if error_code is not None:
                row.error_code = error_code
            if error_message is not None:
                row.error_message = error_message
            if started_at is not None:
                row.started_at = started_at
            if completed_at is not None:
                row.completed_at = completed_at
            row.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(row)
            return self._row_to_run(row)

    async def finalize(self, run_id: UUID, outcome: ResearchRunOutcome) -> ResearchRun:
        """在一个事务中保存终态和全部终态事件。"""
        if not outcome.status.is_terminal:
            raise ValueError("ResearchRunOutcome must use a terminal status")

        async with self._session() as session:
            row = await session.get(ResearchRunRow, str(run_id))
            if row is None:
                raise KeyError(str(run_id))

            current_sequence = await session.scalar(
                select(func.max(ResearchEventRow.sequence)).where(
                    ResearchEventRow.run_id == str(run_id)
                )
            )
            now = datetime.now(UTC)
            event_rows = [
                self._event_draft_to_row(
                    run_id,
                    sequence=(current_sequence or 0) + offset,
                    draft=draft,
                    created_at=now,
                )
                for offset, draft in enumerate(outcome.events, start=1)
            ]

            row.status = outcome.status
            if outcome.progress is not None:
                row.progress = outcome.progress
            if outcome.stage is not None:
                row.current_stage = outcome.stage
            row.report_markdown = outcome.report_markdown
            row.error_code = outcome.error_code
            row.error_message = outcome.error_message
            row.completed_at = now
            row.updated_at = now
            session.add_all(event_rows)
            await session.commit()
            await session.refresh(row)
            return self._row_to_run(row)

    async def save_plan(self, plan: ResearchPlan) -> ResearchPlan:
        row = ResearchPlanRow(
            run_id=str(plan.run_id),
            summary=plan.summary,
            questions=[
                {
                    "id": question.id,
                    "question": question.question,
                    "rationale": question.rationale,
                }
                for question in plan.questions
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
        async with self._session() as session:
            await session.merge(row)
            await session.commit()
        return plan

    async def get_plan(self, run_id: UUID) -> ResearchPlan | None:
        async with self._session() as session:
            row = await session.get(ResearchPlanRow, str(run_id))
            return self._row_to_plan(row) if row else None

    async def append_event(
        self,
        run_id: UUID,
        *,
        event_type: str,
        message: str,
        stage: ResearchStage | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ResearchEvent:
        async with self._session() as session:
            current = await session.scalar(
                select(func.max(ResearchEventRow.sequence)).where(
                    ResearchEventRow.run_id == str(run_id)
                )
            )
            sequence = (current or 0) + 1
            row = ResearchEventRow(
                run_id=str(run_id),
                sequence=sequence,
                type=event_type,
                stage=stage,
                message=message,
                progress=progress,
                payload=payload,
                created_at=datetime.now(UTC),
            )
            session.add(row)
            await session.commit()
            return self._row_to_event(row)

    async def events_after(self, run_id: UUID, sequence: int) -> list[ResearchEvent]:
        async with self._session() as session:
            result = await session.scalars(
                select(ResearchEventRow)
                .where(
                    ResearchEventRow.run_id == str(run_id),
                    ResearchEventRow.sequence > sequence,
                )
                .order_by(ResearchEventRow.sequence)
            )
            return [self._row_to_event(row) for row in result]

    @staticmethod
    def _event_draft_to_row(
        run_id: UUID,
        *,
        sequence: int,
        draft: ResearchEventDraft,
        created_at: datetime,
    ) -> ResearchEventRow:
        return ResearchEventRow(
            run_id=str(run_id),
            sequence=sequence,
            type=draft.type,
            stage=draft.stage,
            message=draft.message,
            progress=draft.progress,
            payload=draft.payload,
            created_at=created_at,
        )

    @staticmethod
    def _run_to_row(run: ResearchRun) -> ResearchRunRow:
        return ResearchRunRow(
            id=str(run.id),
            goal=run.goal,
            title=run.title,
            status=run.status,
            current_stage=run.current_stage,
            progress=run.progress,
            report_markdown=run.report_markdown,
            error_code=run.error_code,
            error_message=run.error_message,
            created_at=run.created_at,
            updated_at=run.updated_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )

    @staticmethod
    def _row_to_run(row: ResearchRunRow) -> ResearchRun:
        return ResearchRun(
            id=UUID(row.id),
            goal=row.goal,
            title=row.title,
            status=row.status,
            current_stage=row.current_stage,
            progress=row.progress,
            report_markdown=row.report_markdown,
            error_code=row.error_code,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _row_to_plan(row: ResearchPlanRow) -> ResearchPlan:
        return ResearchPlan(
            run_id=UUID(row.run_id),
            summary=row.summary,
            questions=tuple(
                ResearchQuestion(
                    id=question["id"],
                    question=question["question"],
                    rationale=question["rationale"],
                )
                for question in row.questions
            ),
            deliverables=tuple(row.deliverables),
            provider=row.provider,
            model=row.model,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.total_tokens,
            duration_ms=row.duration_ms,
            created_at=row.created_at,
        )

    @staticmethod
    def _row_to_event(row: ResearchEventRow) -> ResearchEvent:
        return ResearchEvent(
            sequence=row.sequence,
            run_id=UUID(row.run_id),
            type=row.type,
            stage=row.stage,
            message=row.message,
            progress=row.progress,
            payload=row.payload,
            created_at=row.created_at,
        )
