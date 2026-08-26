import asyncio
import hashlib
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5

from researchflow.core.config import Settings
from researchflow.domain.knowledge import (
    ChunkEmbedding,
    DocumentChunk,
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)
from researchflow.ingestion.retrieval import EmbeddingKnowledgeRetriever
from researchflow.integrations.embedding.base import EmbeddingClient, EmbeddingTask
from researchflow.integrations.embedding.gemini import GeminiEmbeddingClient
from researchflow.integrations.embedding.openai_compatible import (
    OpenAICompatibleEmbeddingClient,
)
from researchflow.persistence import repository as research_repository  # noqa: F401
from researchflow.persistence.database import (
    create_engine,
    create_schema,
    create_session_factory,
)
from researchflow.persistence.knowledge_repository import SqliteKnowledgeRepository

_NAMESPACE = UUID("f3cdb20f-7878-457b-b681-acde33a27d7c")


@dataclass(frozen=True, slots=True)
class EvaluationQuery:
    query: str
    expected_filename: str


QUERIES = (
    EvaluationQuery("如何用可执行测试衡量生成代码的功能正确性", "correctness.md"),
    EvaluationQuery("如何评估生成代码的漏洞、注入和依赖风险", "security.txt"),
    EvaluationQuery("如何衡量开发者完成任务的效率和使用体验", "productivity.md"),
)


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    repository_root = Path(__file__).resolve().parents[1]
    sample_directory = repository_root / "examples" / "knowledge-base"
    settings = Settings()
    if not settings.embedding_model.strip():
        raise SystemExit("请先设置 RESEARCHFLOW_EMBEDDING_MODEL")
    api_key = (
        settings.embedding_api_key.get_secret_value()
        if settings.embedding_api_key is not None
        else None
    )
    if settings.embedding_provider == "gemini":
        if not api_key:
            raise SystemExit("请先设置 RESEARCHFLOW_EMBEDDING_API_KEY")
        embedding_client: EmbeddingClient = GeminiEmbeddingClient(
            base_url=str(settings.embedding_base_url),
            model=settings.embedding_model,
            api_key=api_key,
            timeout_seconds=settings.embedding_timeout_seconds,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
        )
    elif settings.embedding_provider == "openai-compatible":
        embedding_client = OpenAICompatibleEmbeddingClient(
            base_url=str(settings.embedding_base_url),
            model=settings.embedding_model,
            api_key=api_key,
            timeout_seconds=settings.embedding_timeout_seconds,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
        )
    else:
        raise SystemExit(f"不支持的 Embedding Provider：{settings.embedding_provider}")
    with tempfile.TemporaryDirectory(prefix="researchflow-retrieval-") as temporary:
        database_path = Path(temporary) / "evaluation.db"
        engine = create_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        try:
            await create_schema(engine)
            repository = SqliteKnowledgeRepository(create_session_factory(engine))
            document_ids = await _load_samples(
                repository,
                sample_directory,
                embedding_client,
            )
            retriever = EmbeddingKnowledgeRetriever(
                repository,
                embedding_client=embedding_client,
            )
            results = []
            reciprocal_rank_total = 0.0
            top1_count = 0
            for item in QUERIES:
                hits = await retriever.search(item.query, document_ids, limit=3)
                filenames = [hit.document_title for hit in hits]
                rank = (
                    filenames.index(item.expected_filename) + 1
                    if item.expected_filename in filenames
                    else 0
                )
                top1_count += int(rank == 1)
                reciprocal_rank_total += 1 / rank if rank else 0
                results.append(
                    {
                        **asdict(item),
                        "rank": rank,
                        "results": [
                            {
                                "filename": hit.document_title,
                                "score": round(hit.score, 4),
                            }
                            for hit in hits
                        ],
                    }
                )
        finally:
            await engine.dispose()
    top1_accuracy = round(top1_count / len(QUERIES), 3)
    mrr_at_3 = round(reciprocal_rank_total / len(QUERIES), 3)
    print(
        json.dumps(
            {
                "sample_count": len(document_ids),
                "query_count": len(QUERIES),
                "provider": settings.embedding_provider,
                "model": settings.embedding_model,
                "top1_accuracy": top1_accuracy,
                "mrr_at_3": mrr_at_3,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0 if top1_accuracy == 1 else 1


async def _load_samples(
    repository: SqliteKnowledgeRepository,
    sample_directory: Path,
    embedding_client: EmbeddingClient,
) -> tuple[UUID, ...]:
    documents: list[tuple[UUID, Path, str]] = []
    for path in sorted(sample_directory.iterdir()):
        content = path.read_text(encoding="utf-8").strip()
        document_id = uuid5(_NAMESPACE, path.name)
        documents.append((document_id, path, content))
    vectors = await embedding_client.embed(
        tuple(content for _, _, content in documents),
        task=EmbeddingTask.DOCUMENT,
    )
    document_ids = []
    for (document_id, path, content), vector in zip(documents, vectors, strict=True):
        now = datetime.now(UTC)
        await repository.create(
            KnowledgeDocument(
                id=document_id,
                original_filename=path.name,
                media_type="text/markdown" if path.suffix == ".md" else "text/plain",
                size_bytes=len(content.encode()),
                sha256=hashlib.sha256(content.encode()).hexdigest(),
                storage_name=f"{document_id}{path.suffix}",
                status=KnowledgeDocumentStatus.PROCESSING,
                chunk_count=0,
                error_code=None,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
        )
        await repository.replace_chunks(
            document_id,
            (
                DocumentChunk(
                    id=f"{document_id}:1",
                    document_id=document_id,
                    ordinal=1,
                    content=content,
                    locator="完整样例",
                    page_number=None,
                    start_line=1,
                    end_line=None,
                ),
            ),
            (
                ChunkEmbedding(
                    chunk_id=f"{document_id}:1",
                    model=embedding_client.model,
                    vector=vector,
                ),
            ),
        )
        document_ids.append(document_id)
    return tuple(document_ids)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
