import math
from typing import Protocol
from uuid import UUID

from researchflow.domain.knowledge import KnowledgeSearchHit
from researchflow.integrations.embedding.base import (
    EmbeddingClient,
    EmbeddingClientError,
    EmbeddingTask,
)
from researchflow.persistence.knowledge_repository import SqliteKnowledgeRepository


class KnowledgeRetriever(Protocol):
    async def search(
        self,
        query: str,
        document_ids: tuple[UUID, ...],
        *,
        limit: int,
    ) -> tuple[KnowledgeSearchHit, ...]: ...


class EmbeddingKnowledgeRetriever:
    """用同一 Embedding 模型查询并排列所选 SQLite 文档片段。"""

    def __init__(
        self,
        repository: SqliteKnowledgeRepository,
        *,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._repository = repository
        self._embedding_client = embedding_client

    async def search(
        self,
        query: str,
        document_ids: tuple[UUID, ...],
        *,
        limit: int,
    ) -> tuple[KnowledgeSearchHit, ...]:
        normalized_query = query.strip()
        if not document_ids or not normalized_query:
            return ()
        candidates = await self._repository.list_embedded_chunks_for_documents(
            document_ids,
            model=self._embedding_client.model,
        )
        if not candidates:
            raise EmbeddingClientError(
                "EMBEDDING_REPROCESS_REQUIRED",
                "所选文档没有当前模型生成的向量，请重新处理文档",
            )
        query_vectors = await self._embedding_client.embed(
            (normalized_query,),
            task=EmbeddingTask.QUERY,
        )
        if len(query_vectors) != 1:
            raise EmbeddingClientError(
                "EMBEDDING_INVALID_RESPONSE", "Embedding 服务没有返回查询向量"
            )
        query_vector = query_vectors[0]
        hits: list[KnowledgeSearchHit] = []
        for title, chunk, embedding in candidates:
            if len(query_vector) != len(embedding.vector):
                raise EmbeddingClientError(
                    "EMBEDDING_DIMENSION_MISMATCH",
                    "查询向量与文档向量维度不一致，请重新处理文档",
                )
            score = _cosine_similarity(query_vector, embedding.vector)
            hits.append(
                KnowledgeSearchHit(
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    document_title=title,
                    content=chunk.content,
                    locator=chunk.locator,
                    score=score,
                )
            )
        return tuple(sorted(hits, key=lambda item: (-item.score, item.chunk_id))[:limit])


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
