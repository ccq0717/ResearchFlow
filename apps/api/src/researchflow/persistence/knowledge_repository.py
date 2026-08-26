from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from researchflow.domain.knowledge import (
    DocumentChunk,
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)
from researchflow.persistence.database import Base


class KnowledgeDocumentRow(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    storage_name: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[KnowledgeDocumentStatus] = mapped_column(Enum(KnowledgeDocumentStatus))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DocumentChunkRow(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(160))
    page_number: Mapped[int | None] = mapped_column(Integer)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)


class ResearchRunDocumentRow(Base):
    __tablename__ = "research_run_documents"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), primary_key=True
    )


class SqliteKnowledgeRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sessions = session_factory

    async def create(self, document: KnowledgeDocument) -> None:
        async with self._sessions() as session:
            session.add(self._to_row(document))
            await session.commit()

    async def count(self) -> int:
        async with self._sessions() as session:
            return int(await session.scalar(select(func.count(KnowledgeDocumentRow.id))) or 0)

    async def get(self, document_id: UUID) -> KnowledgeDocument | None:
        async with self._sessions() as session:
            row = await session.get(KnowledgeDocumentRow, str(document_id))
            if row is None:
                return None
            chunk_count = await self._chunk_count(session, row.id)
            return self._to_domain(row, chunk_count)

    async def find_by_sha256(self, sha256: str) -> KnowledgeDocument | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(KnowledgeDocumentRow).where(KnowledgeDocumentRow.sha256 == sha256)
            )
            if row is None:
                return None
            chunk_count = await self._chunk_count(session, row.id)
            return self._to_domain(row, chunk_count)

    async def list_documents(self) -> tuple[KnowledgeDocument, ...]:
        async with self._sessions() as session:
            rows = tuple(
                await session.scalars(
                    select(KnowledgeDocumentRow).order_by(KnowledgeDocumentRow.created_at.desc())
                )
            )
            counts = {
                document_id: count
                for document_id, count in (
                    await session.execute(
                        select(
                            DocumentChunkRow.document_id, func.count(DocumentChunkRow.id)
                        ).group_by(DocumentChunkRow.document_id)
                    )
                ).all()
            }
            return tuple(self._to_domain(row, int(counts.get(row.id, 0))) for row in rows)

    async def list_chunks(self, document_id: UUID) -> tuple[DocumentChunk, ...]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(DocumentChunkRow)
                .where(DocumentChunkRow.document_id == str(document_id))
                .order_by(DocumentChunkRow.ordinal)
            )
            return tuple(self._chunk_to_domain(row) for row in rows)

    async def list_chunks_for_documents(
        self,
        document_ids: tuple[UUID, ...],
    ) -> tuple[tuple[str, DocumentChunk], ...]:
        if not document_ids:
            return ()
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(KnowledgeDocumentRow.original_filename, DocumentChunkRow)
                    .join(
                        DocumentChunkRow,
                        DocumentChunkRow.document_id == KnowledgeDocumentRow.id,
                    )
                    .where(
                        KnowledgeDocumentRow.id.in_([str(item) for item in document_ids]),
                        KnowledgeDocumentRow.status == KnowledgeDocumentStatus.READY,
                    )
                    .order_by(KnowledgeDocumentRow.id, DocumentChunkRow.ordinal)
                )
            ).all()
            return tuple((title, self._chunk_to_domain(row)) for title, row in rows)

    async def link_run(self, run_id: UUID, document_ids: tuple[UUID, ...]) -> None:
        async with self._sessions() as session:
            session.add_all(
                ResearchRunDocumentRow(run_id=str(run_id), document_id=str(document_id))
                for document_id in document_ids
            )
            await session.commit()

    async def list_run_document_ids(self, run_id: UUID) -> tuple[UUID, ...]:
        async with self._sessions() as session:
            values = await session.scalars(
                select(ResearchRunDocumentRow.document_id)
                .where(ResearchRunDocumentRow.run_id == str(run_id))
                .order_by(ResearchRunDocumentRow.document_id)
            )
            return tuple(UUID(value) for value in values)

    async def mark_processing(self, document_id: UUID) -> None:
        await self._update_status(document_id, KnowledgeDocumentStatus.PROCESSING, None, None)

    async def mark_failed(self, document_id: UUID, code: str, message: str) -> None:
        async with self._sessions() as session:
            row = await session.get(KnowledgeDocumentRow, str(document_id))
            if row is None:
                raise KeyError(str(document_id))
            await session.execute(
                delete(DocumentChunkRow).where(DocumentChunkRow.document_id == str(document_id))
            )
            row.status = KnowledgeDocumentStatus.FAILED
            row.error_code = code
            row.error_message = message
            row.updated_at = datetime.now(UTC)
            await session.commit()

    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: tuple[DocumentChunk, ...],
    ) -> None:
        async with self._sessions() as session:
            row = await session.get(KnowledgeDocumentRow, str(document_id))
            if row is None:
                raise KeyError(str(document_id))
            await session.execute(
                delete(DocumentChunkRow).where(DocumentChunkRow.document_id == str(document_id))
            )
            session.add_all(
                DocumentChunkRow(
                    id=chunk.id,
                    document_id=str(chunk.document_id),
                    ordinal=chunk.ordinal,
                    content=chunk.content,
                    locator=chunk.locator,
                    page_number=chunk.page_number,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                )
                for chunk in chunks
            )
            row.status = KnowledgeDocumentStatus.READY
            row.error_code = None
            row.error_message = None
            row.updated_at = datetime.now(UTC)
            await session.commit()

    async def delete(self, document_id: UUID) -> bool:
        async with self._sessions() as session:
            row = await session.get(KnowledgeDocumentRow, str(document_id))
            if row is None:
                return False
            await session.execute(
                delete(DocumentChunkRow).where(DocumentChunkRow.document_id == str(document_id))
            )
            await session.execute(
                delete(ResearchRunDocumentRow).where(
                    ResearchRunDocumentRow.document_id == str(document_id)
                )
            )
            await session.delete(row)
            await session.commit()
            return True

    async def _update_status(
        self,
        document_id: UUID,
        status: KnowledgeDocumentStatus,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        async with self._sessions() as session:
            row = await session.get(KnowledgeDocumentRow, str(document_id))
            if row is None:
                raise KeyError(str(document_id))
            row.status = status
            row.error_code = error_code
            row.error_message = error_message
            row.updated_at = datetime.now(UTC)
            await session.commit()

    @staticmethod
    async def _chunk_count(session, document_id: str) -> int:
        value = await session.scalar(
            select(func.count(DocumentChunkRow.id)).where(
                DocumentChunkRow.document_id == document_id
            )
        )
        return int(value or 0)

    @staticmethod
    def _to_row(document: KnowledgeDocument) -> KnowledgeDocumentRow:
        return KnowledgeDocumentRow(
            id=str(document.id),
            original_filename=document.original_filename,
            media_type=document.media_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            storage_name=document.storage_name,
            status=document.status,
            error_code=document.error_code,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @staticmethod
    def _to_domain(row: KnowledgeDocumentRow, chunk_count: int) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=UUID(row.id),
            original_filename=row.original_filename,
            media_type=row.media_type,
            size_bytes=row.size_bytes,
            sha256=row.sha256,
            storage_name=row.storage_name,
            status=row.status,
            chunk_count=chunk_count,
            error_code=row.error_code,
            error_message=row.error_message,
            created_at=SqliteKnowledgeRepository._as_utc(row.created_at),
            updated_at=SqliteKnowledgeRepository._as_utc(row.updated_at),
        )

    @staticmethod
    def _chunk_to_domain(row: DocumentChunkRow) -> DocumentChunk:
        return DocumentChunk(
            id=row.id,
            document_id=UUID(row.document_id),
            ordinal=row.ordinal,
            content=row.content,
            locator=row.locator,
            page_number=row.page_number,
            start_line=row.start_line,
            end_line=row.end_line,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
