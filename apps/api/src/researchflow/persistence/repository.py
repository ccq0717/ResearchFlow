import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from researchflow.domain.citations import build_citation_audit
from researchflow.domain.research import (
    Claim,
    Evidence,
    ResearchEvent,
    ResearchEventDraft,
    ResearchMaterials,
    ResearchPlan,
    ResearchQuestion,
    ResearchRun,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
    ResearchTask,
    ResearchTaskStatus,
    Source,
    SourceOrigin,
    SourceType,
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


class ResearchTaskRow(Base):
    __tablename__ = "research_tasks"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(80))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[ResearchTaskStatus] = mapped_column(Enum(ResearchTaskStatus))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceRow(Base):
    __tablename__ = "research_sources"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceMetadataRow(Base):
    __tablename__ = "research_source_metadata"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publisher: Mapped[str | None] = mapped_column(Text)


class SourceOriginRow(Base):
    __tablename__ = "research_source_origins"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    origin: Mapped[SourceOrigin] = mapped_column(Enum(SourceOrigin))
    knowledge_document_id: Mapped[str | None] = mapped_column(String(36))
    locator: Mapped[str | None] = mapped_column(String(160))


class EvidenceRow(Base):
    __tablename__ = "research_evidence"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(80))
    question_id: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[str] = mapped_column(String(80))
    excerpt: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClaimRow(Base):
    __tablename__ = "research_claims"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClaimEvidenceRow(Base):
    __tablename__ = "research_claim_evidence"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    claim_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(80), primary_key=True)


class SqliteResearchRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sessions = session_factory

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        session = self._sessions()
        try:
            yield session
        except asyncio.CancelledError:
            # SQLite 提交由工作线程执行；取消时仍需完成回滚，避免遗留写锁。
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
                    "search_query": question.search_query,
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

    async def save_materials(
        self,
        *,
        tasks: tuple[ResearchTask, ...] = (),
        sources: tuple[Source, ...] = (),
        evidence: tuple[Evidence, ...] = (),
        claims: tuple[Claim, ...] = (),
    ) -> None:
        async with self._session() as session:
            for task in tasks:
                await session.merge(
                    ResearchTaskRow(
                        run_id=str(task.run_id),
                        id=task.id,
                        question_id=task.question_id,
                        query=task.query,
                        status=task.status,
                        created_at=task.created_at,
                    )
                )
            for source in sources:
                await session.merge(
                    SourceRow(
                        run_id=str(source.run_id),
                        id=source.id,
                        task_id=source.task_id,
                        title=source.title,
                        url=source.url or "",
                        snippet=source.snippet,
                        retrieved_at=source.retrieved_at,
                    )
                )
                await session.merge(
                    SourceMetadataRow(
                        run_id=str(source.run_id),
                        source_id=source.id,
                        source_type=source.source_type,
                        author=source.author,
                        published_at=source.published_at,
                        publisher=source.publisher,
                    )
                )
                await session.merge(
                    SourceOriginRow(
                        run_id=str(source.run_id),
                        source_id=source.id,
                        origin=source.origin,
                        knowledge_document_id=(
                            str(source.knowledge_document_id)
                            if source.knowledge_document_id is not None
                            else None
                        ),
                        locator=source.locator,
                    )
                )
            for item in evidence:
                await session.merge(
                    EvidenceRow(
                        run_id=str(item.run_id),
                        id=item.id,
                        task_id=item.task_id,
                        question_id=item.question_id,
                        source_id=item.source_id,
                        excerpt=item.excerpt,
                        summary=item.summary,
                        created_at=item.created_at,
                    )
                )
            for claim in claims:
                await session.merge(
                    ClaimRow(
                        run_id=str(claim.run_id),
                        id=claim.id,
                        question_id=claim.question_id,
                        text=claim.text,
                        created_at=claim.created_at,
                    )
                )
                for evidence_id in claim.evidence_ids:
                    await session.merge(
                        ClaimEvidenceRow(
                            run_id=str(claim.run_id),
                            claim_id=claim.id,
                            evidence_id=evidence_id,
                        )
                    )
            await session.commit()

    async def get_materials(self, run_id: UUID) -> ResearchMaterials:
        async with self._session() as session:
            task_rows = await session.scalars(
                select(ResearchTaskRow)
                .where(ResearchTaskRow.run_id == str(run_id))
                .order_by(ResearchTaskRow.id)
            )
            source_rows = await session.scalars(
                select(SourceRow).where(SourceRow.run_id == str(run_id)).order_by(SourceRow.id)
            )
            metadata_rows = await session.scalars(
                select(SourceMetadataRow).where(SourceMetadataRow.run_id == str(run_id))
            )
            origin_rows = await session.scalars(
                select(SourceOriginRow).where(SourceOriginRow.run_id == str(run_id))
            )
            evidence_rows = await session.scalars(
                select(EvidenceRow)
                .where(EvidenceRow.run_id == str(run_id))
                .order_by(EvidenceRow.id)
            )
            claim_rows = await session.scalars(
                select(ClaimRow).where(ClaimRow.run_id == str(run_id)).order_by(ClaimRow.id)
            )
            claim_evidence_rows = await session.scalars(
                select(ClaimEvidenceRow)
                .where(ClaimEvidenceRow.run_id == str(run_id))
                .order_by(ClaimEvidenceRow.claim_id, ClaimEvidenceRow.evidence_id)
            )
            metadata_by_source = {row.source_id: row for row in metadata_rows}
            origin_by_source = {row.source_id: row for row in origin_rows}
            evidence_items = tuple(self._row_to_evidence(row) for row in evidence_rows)
            evidence_by_claim: dict[str, list[str]] = {}
            for row in claim_evidence_rows:
                evidence_by_claim.setdefault(row.claim_id, []).append(row.evidence_id)
            source_items = tuple(
                self._row_to_source(
                    row,
                    metadata_by_source.get(row.id),
                    origin_by_source.get(row.id),
                )
                for row in source_rows
            )
            claim_items = tuple(
                self._row_to_claim(row, tuple(evidence_by_claim.get(row.id, ())))
                for row in claim_rows
            )
            return ResearchMaterials(
                run_id=run_id,
                tasks=tuple(self._row_to_task(row) for row in task_rows),
                sources=source_items,
                evidence=evidence_items,
                claims=claim_items,
                citation_audit=build_citation_audit(claim_items, evidence_items, source_items),
            )

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
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

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
            created_at=SqliteResearchRepository._as_utc(row.created_at),
            updated_at=SqliteResearchRepository._as_utc(row.updated_at),
            started_at=SqliteResearchRepository._as_utc(row.started_at),
            completed_at=SqliteResearchRepository._as_utc(row.completed_at),
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
                    search_query=question.get("search_query", question["question"]),
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
            created_at=SqliteResearchRepository._as_utc(row.created_at),
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
            created_at=SqliteResearchRepository._as_utc(row.created_at),
        )

    @staticmethod
    def _row_to_task(row: ResearchTaskRow) -> ResearchTask:
        return ResearchTask(
            id=row.id,
            run_id=UUID(row.run_id),
            question_id=row.question_id,
            query=row.query,
            status=row.status,
            created_at=SqliteResearchRepository._as_utc(row.created_at),
        )

    @staticmethod
    def _row_to_source(
        row: SourceRow,
        metadata: SourceMetadataRow | None = None,
        origin: SourceOriginRow | None = None,
    ) -> Source:
        source_origin = origin.origin if origin else SourceOrigin.WEB
        return Source(
            id=row.id,
            run_id=UUID(row.run_id),
            task_id=row.task_id,
            title=row.title,
            url=row.url if source_origin is SourceOrigin.WEB else None,
            snippet=row.snippet,
            retrieved_at=SqliteResearchRepository._as_utc(row.retrieved_at),
            source_type=metadata.source_type if metadata else SourceType.OTHER,
            author=metadata.author if metadata else None,
            published_at=(
                SqliteResearchRepository._as_utc(metadata.published_at) if metadata else None
            ),
            publisher=metadata.publisher if metadata else None,
            origin=source_origin,
            knowledge_document_id=(
                UUID(origin.knowledge_document_id)
                if origin is not None and origin.knowledge_document_id is not None
                else None
            ),
            locator=origin.locator if origin else None,
        )

    @staticmethod
    def _row_to_evidence(row: EvidenceRow) -> Evidence:
        return Evidence(
            id=row.id,
            run_id=UUID(row.run_id),
            task_id=row.task_id,
            question_id=row.question_id,
            source_id=row.source_id,
            excerpt=row.excerpt,
            summary=row.summary,
            created_at=SqliteResearchRepository._as_utc(row.created_at),
        )

    @staticmethod
    def _row_to_claim(row: ClaimRow, evidence_ids: tuple[str, ...]) -> Claim:
        return Claim(
            id=row.id,
            run_id=UUID(row.run_id),
            question_id=row.question_id,
            text=row.text,
            evidence_ids=evidence_ids,
            created_at=SqliteResearchRepository._as_utc(row.created_at),
        )
