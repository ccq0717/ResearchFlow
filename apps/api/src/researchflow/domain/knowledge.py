from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class KnowledgeDocumentStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    storage_name: str
    status: KnowledgeDocumentStatus
    chunk_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: str
    document_id: UUID
    ordinal: int
    content: str
    locator: str
    page_number: int | None
    start_line: int | None
    end_line: int | None


@dataclass(frozen=True, slots=True)
class ChunkEmbedding:
    chunk_id: str
    model: str
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeSearchHit:
    document_id: UUID
    chunk_id: str
    document_title: str
    content: str
    locator: str
    score: float
