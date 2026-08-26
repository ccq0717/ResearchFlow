import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from researchflow.domain.knowledge import (
    DocumentChunk,
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)
from researchflow.ingestion.documents import DocumentParsingError, parse_document
from researchflow.persistence.knowledge_repository import SqliteKnowledgeRepository

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


class KnowledgeLibraryError(Exception):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class KnowledgeLibrary:
    """隐藏上传安全、文件存储、解析和文档状态转换的知识库模块。"""

    def __init__(
        self,
        repository: SqliteKnowledgeRepository,
        *,
        upload_directory: Path,
        max_document_bytes: int,
        max_document_count: int,
        max_selection_count: int,
        chunk_size: int,
        max_extracted_characters: int,
        max_pdf_pages: int,
        max_pdf_page_stream_bytes: int,
    ) -> None:
        self._repository = repository
        self._upload_directory = upload_directory.resolve()
        self._max_document_bytes = max_document_bytes
        self._max_document_count = max_document_count
        self._max_selection_count = max_selection_count
        self._chunk_size = chunk_size
        self._max_extracted_characters = max_extracted_characters
        self._max_pdf_pages = max_pdf_pages
        self._max_pdf_page_stream_bytes = max_pdf_page_stream_bytes

    @property
    def max_document_bytes(self) -> int:
        return self._max_document_bytes

    async def upload(self, filename: str | None, data: bytes) -> KnowledgeDocument:
        safe_filename, suffix, media_type = self._validate_upload(filename, data)
        if await self._repository.count() >= self._max_document_count:
            raise KnowledgeLibraryError(
                "KNOWLEDGE_DOCUMENT_LIMIT_REACHED",
                f"本地知识库最多保存 {self._max_document_count} 个文档",
            )
        digest = hashlib.sha256(data).hexdigest()
        duplicate = await self._repository.find_by_sha256(digest)
        if duplicate is not None:
            raise KnowledgeLibraryError(
                "KNOWLEDGE_DOCUMENT_DUPLICATE",
                f"相同内容已经以“{duplicate.original_filename}”上传",
            )

        document_id = uuid4()
        storage_name = f"{document_id}{suffix}"
        now = datetime.now(UTC)
        document = KnowledgeDocument(
            id=document_id,
            original_filename=safe_filename,
            media_type=media_type,
            size_bytes=len(data),
            sha256=digest,
            storage_name=storage_name,
            status=KnowledgeDocumentStatus.PROCESSING,
            chunk_count=0,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        target = self._storage_path(storage_name)
        await asyncio.to_thread(self._write_file_atomically, target, data)
        try:
            await self._repository.create(document)
        except Exception:
            await asyncio.to_thread(target.unlink, True)
            raise
        await self._process(document)
        stored = await self._repository.get(document.id)
        if stored is None:
            raise RuntimeError("文档保存后无法重新读取")
        return stored

    async def list_documents(self) -> tuple[KnowledgeDocument, ...]:
        return await self._repository.list_documents()

    async def validate_selection(self, document_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        unique_ids = tuple(dict.fromkeys(document_ids))
        if len(unique_ids) > self._max_selection_count:
            raise KnowledgeLibraryError(
                "KNOWLEDGE_SELECTION_TOO_LARGE",
                f"一次研究最多选择 {self._max_selection_count} 个本地文档",
            )
        for document_id in unique_ids:
            document = await self._repository.get(document_id)
            if document is None:
                raise KnowledgeLibraryError(
                    "KNOWLEDGE_DOCUMENT_NOT_FOUND",
                    "选择的知识文档不存在",
                )
            if document.status is not KnowledgeDocumentStatus.READY:
                raise KnowledgeLibraryError(
                    "KNOWLEDGE_DOCUMENT_NOT_READY",
                    f"文档“{document.original_filename}”尚未成功处理",
                )
        return unique_ids

    async def link_run(self, run_id: UUID, document_ids: tuple[UUID, ...]) -> None:
        await self._repository.link_run(run_id, document_ids)

    async def list_run_document_ids(self, run_id: UUID) -> tuple[UUID, ...]:
        return await self._repository.list_run_document_ids(run_id)

    async def get(self, document_id: UUID) -> KnowledgeDocument | None:
        return await self._repository.get(document_id)

    async def list_chunks(self, document_id: UUID) -> tuple[DocumentChunk, ...]:
        if await self._repository.get(document_id) is None:
            raise KnowledgeLibraryError("KNOWLEDGE_DOCUMENT_NOT_FOUND", "知识文档不存在")
        return await self._repository.list_chunks(document_id)

    async def read_content(self, document_id: UUID) -> tuple[KnowledgeDocument, bytes]:
        document = await self._repository.get(document_id)
        if document is None:
            raise KnowledgeLibraryError("KNOWLEDGE_DOCUMENT_NOT_FOUND", "知识文档不存在")
        target = self._storage_path(document.storage_name)
        try:
            content = await asyncio.to_thread(target.read_bytes)
        except OSError as error:
            raise KnowledgeLibraryError(
                "DOCUMENT_STORAGE_ERROR",
                "无法读取已保存的文档文件",
            ) from error
        return document, content

    async def reprocess(self, document_id: UUID) -> KnowledgeDocument:
        document = await self._repository.get(document_id)
        if document is None:
            raise KnowledgeLibraryError("KNOWLEDGE_DOCUMENT_NOT_FOUND", "知识文档不存在")
        await self._repository.mark_processing(document_id)
        await self._process(document)
        refreshed = await self._repository.get(document_id)
        if refreshed is None:
            raise RuntimeError("文档重新处理后无法读取")
        return refreshed

    async def delete(self, document_id: UUID) -> None:
        document = await self._repository.get(document_id)
        if document is None:
            raise KnowledgeLibraryError("KNOWLEDGE_DOCUMENT_NOT_FOUND", "知识文档不存在")
        target = self._storage_path(document.storage_name)
        await asyncio.to_thread(target.unlink, True)
        deleted = await self._repository.delete(document_id)
        if not deleted:
            raise KnowledgeLibraryError("KNOWLEDGE_DOCUMENT_NOT_FOUND", "知识文档不存在")

    async def _process(self, document: KnowledgeDocument) -> None:
        target = self._storage_path(document.storage_name)
        try:
            data = await asyncio.to_thread(target.read_bytes)
            parsed = await asyncio.to_thread(
                parse_document,
                document.original_filename,
                data,
                chunk_size=self._chunk_size,
                max_extracted_characters=self._max_extracted_characters,
                max_pdf_pages=self._max_pdf_pages,
                max_pdf_page_stream_bytes=self._max_pdf_page_stream_bytes,
            )
            chunks = tuple(
                DocumentChunk(
                    id=f"{document.id}:{index}",
                    document_id=document.id,
                    ordinal=index,
                    content=item.content,
                    locator=item.locator,
                    page_number=item.page_number,
                    start_line=item.start_line,
                    end_line=item.end_line,
                )
                for index, item in enumerate(parsed, start=1)
            )
            await self._repository.replace_chunks(document.id, chunks)
        except DocumentParsingError as error:
            await self._repository.mark_failed(document.id, error.code, error.public_message)
        except OSError:
            await self._repository.mark_failed(
                document.id,
                "DOCUMENT_STORAGE_ERROR",
                "无法读取已保存的文档文件",
            )

    def _validate_upload(self, filename: str | None, data: bytes) -> tuple[str, str, str]:
        safe_filename = Path(filename or "").name.strip()
        if not safe_filename or len(safe_filename) > 255:
            raise KnowledgeLibraryError("DOCUMENT_FILENAME_INVALID", "文件名为空或过长")
        suffix = Path(safe_filename).suffix.lower()
        media_type = _MEDIA_TYPES.get(suffix)
        if media_type is None:
            raise KnowledgeLibraryError(
                "DOCUMENT_TYPE_UNSUPPORTED",
                "仅支持 PDF、Markdown 和纯文本文件",
            )
        if not data:
            raise KnowledgeLibraryError("DOCUMENT_EMPTY", "不能上传空文件")
        if len(data) > self._max_document_bytes:
            size_mb = self._max_document_bytes // (1024 * 1024)
            raise KnowledgeLibraryError(
                "DOCUMENT_TOO_LARGE",
                f"单个文档不能超过 {size_mb} MB",
            )
        if suffix == ".pdf" and not data.startswith(b"%PDF-"):
            raise KnowledgeLibraryError(
                "DOCUMENT_INVALID_PDF",
                "文件扩展名为 PDF，但内容不是有效 PDF",
            )
        return safe_filename, suffix, media_type

    def _storage_path(self, storage_name: str) -> Path:
        target = (self._upload_directory / storage_name).resolve()
        if target.parent != self._upload_directory:
            raise RuntimeError("非法知识文档存储路径")
        return target

    def _write_file_atomically(self, target: Path, data: bytes) -> None:
        self._upload_directory.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        temporary.write_bytes(data)
        temporary.replace(target)
