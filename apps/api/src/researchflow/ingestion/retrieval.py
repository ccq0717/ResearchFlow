import math
import re
from collections import Counter
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from researchflow.domain.knowledge import KnowledgeSearchHit
from researchflow.persistence.knowledge_repository import SqliteKnowledgeRepository

_LATIN_WORD = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
_CJK_CHAR = re.compile(r"[\u3400-\u9fff]")


class RetrievalMode(StrEnum):
    LEXICAL = "lexical"
    VECTOR = "vector"
    HYBRID = "hybrid"


class KnowledgeRetriever(Protocol):
    async def search(
        self,
        query: str,
        document_ids: tuple[UUID, ...],
        *,
        limit: int,
    ) -> tuple[KnowledgeSearchHit, ...]: ...


class LocalKnowledgeRetriever:
    """用轻量词项与字符 n-gram 向量检索本地 SQLite 文档块。"""

    def __init__(
        self,
        repository: SqliteKnowledgeRepository,
        *,
        mode: RetrievalMode = RetrievalMode.HYBRID,
    ) -> None:
        self._repository = repository
        self._mode = mode

    async def search(
        self,
        query: str,
        document_ids: tuple[UUID, ...],
        *,
        limit: int,
    ) -> tuple[KnowledgeSearchHit, ...]:
        candidates = await self._repository.list_chunks_for_documents(document_ids)
        if not candidates or not query.strip():
            return ()
        lexical_scores = [_lexical_score(query, chunk.content) for _, chunk in candidates]
        vector_scores = [_vector_score(query, chunk.content) for _, chunk in candidates]
        lexical_max = max(lexical_scores, default=0.0) or 1.0
        vector_max = max(vector_scores, default=0.0) or 1.0
        hits = []
        for (title, chunk), lexical, vector in zip(
            candidates,
            lexical_scores,
            vector_scores,
            strict=True,
        ):
            if self._mode is RetrievalMode.LEXICAL:
                score = lexical
            elif self._mode is RetrievalMode.VECTOR:
                score = vector
            else:
                score = 0.45 * lexical / lexical_max + 0.55 * vector / vector_max
            if score > 0:
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


def _lexical_score(query: str, content: str) -> float:
    query_terms = Counter(_terms(query))
    content_terms = Counter(_terms(content))
    if not query_terms or not content_terms:
        return 0.0
    overlap = sum(min(count, content_terms[term]) for term, count in query_terms.items())
    return overlap / math.sqrt(sum(query_terms.values()) * sum(content_terms.values()))


def _vector_score(query: str, content: str) -> float:
    query_vector = Counter(_character_ngrams(query))
    content_vector = Counter(_character_ngrams(content))
    if not query_vector or not content_vector:
        return 0.0
    dot = sum(value * content_vector[key] for key, value in query_vector.items())
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    content_norm = math.sqrt(sum(value * value for value in content_vector.values()))
    return dot / (query_norm * content_norm) if query_norm and content_norm else 0.0


def _terms(value: str) -> tuple[str, ...]:
    lowered = value.casefold()
    latin = _LATIN_WORD.findall(lowered)
    cjk = _CJK_CHAR.findall(lowered)
    cjk_bigrams = ["".join(cjk[index : index + 2]) for index in range(len(cjk) - 1)]
    return tuple((*latin, *cjk, *cjk_bigrams))


def _character_ngrams(value: str) -> tuple[str, ...]:
    normalized = "".join(character for character in value.casefold() if character.isalnum())
    if len(normalized) < 3:
        return (normalized,) if normalized else ()
    return tuple(normalized[index : index + 3] for index in range(len(normalized) - 2))
