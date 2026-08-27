import json
import math
from typing import Any
from urllib.parse import quote

import httpx

from researchflow.integrations.embedding.base import EmbeddingClientError, EmbeddingTask


class GeminiEmbeddingClient:
    """通过 Gemini batchEmbedContents 生成区分文档与查询用途的向量。"""

    _INSTRUCTION_BASED_MODELS = frozenset({"gemini-embedding-2"})

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
        dimensions: int | None = None,
        batch_size: int = 32,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized_model = model.removeprefix("models/").strip()
        if not normalized_model:
            raise ValueError("Gemini Embedding 模型名不能为空")
        encoded_model = quote(normalized_model, safe="-._")
        self._endpoint = f"{base_url.rstrip('/')}/models/{encoded_model}:batchEmbedContents"
        self._model = normalized_model
        self._uses_instruction_prefix = normalized_model in self._INSTRUCTION_BASED_MODELS
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._transport = transport

    @property
    def model(self) -> str:
        dimensions = self._dimensions if self._dimensions is not None else "default"
        strategy = "search-prefix-v1" if self._uses_instruction_prefix else "task-type-v1"
        return f"gemini:{self._model}:{dimensions}:{strategy}"

    async def embed(
        self,
        texts: tuple[str, ...],
        *,
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(await self._embed_batch(texts[start : start + self._batch_size], task))
        return tuple(vectors)

    async def _embed_batch(
        self,
        texts: tuple[str, ...],
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]:
        config: dict[str, Any] = {}
        if not self._uses_instruction_prefix:
            config["taskType"] = (
                "RETRIEVAL_DOCUMENT" if task is EmbeddingTask.DOCUMENT else "RETRIEVAL_QUERY"
            )
        if self._dimensions is not None:
            config["outputDimensionality"] = self._dimensions
        requests = [
            {
                "model": f"models/{self._model}",
                "content": {"parts": [{"text": self._prepare_text(text, task)}]},
                "embedContentConfig": config,
            }
            for text in texts
        ]
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self._api_key,
                    },
                    json={"requests": requests},
                )
                response.raise_for_status()
            vectors = self._parse_vectors(response.json(), len(texts))
            self._validate_configured_dimensions(vectors)
            return vectors
        except httpx.TimeoutException as error:
            raise EmbeddingClientError(
                "EMBEDDING_TIMEOUT", "Gemini Embedding 服务响应超时，请稍后重试"
            ) from error
        except httpx.HTTPStatusError as error:
            raise EmbeddingClientError(
                "EMBEDDING_HTTP_ERROR",
                f"Gemini Embedding 服务返回错误状态（HTTP {error.response.status_code}）",
            ) from error
        except httpx.RequestError as error:
            raise EmbeddingClientError(
                "EMBEDDING_CONNECTION_ERROR", "无法连接 Gemini Embedding 服务"
            ) from error
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise EmbeddingClientError(
                "EMBEDDING_INVALID_RESPONSE", "Gemini Embedding 返回的数据格式无效"
            ) from error

    def _prepare_text(self, text: str, task: EmbeddingTask) -> str:
        if not self._uses_instruction_prefix:
            return text
        if task is EmbeddingTask.DOCUMENT:
            return f"title: none | text: {text}"
        return f"task: search result | query: {text}"

    @staticmethod
    def _parse_vectors(payload: object, expected_count: int) -> tuple[tuple[float, ...], ...]:
        if not isinstance(payload, dict) or not isinstance(payload.get("embeddings"), list):
            raise TypeError("embeddings must be a list")
        raw_embeddings = payload["embeddings"]
        if len(raw_embeddings) != expected_count:
            raise ValueError("embedding response count does not match input")
        vectors: list[tuple[float, ...]] = []
        dimensions: int | None = None
        for item in raw_embeddings:
            if not isinstance(item, dict) or not isinstance(item.get("values"), list):
                raise TypeError("invalid embedding item")
            vector = tuple(float(value) for value in item["values"])
            if not vector or not all(math.isfinite(value) for value in vector):
                raise ValueError("embedding vector is empty or non-finite")
            dimensions = dimensions or len(vector)
            if len(vector) != dimensions:
                raise ValueError("embedding dimensions are inconsistent")
            vectors.append(vector)
        return tuple(vectors)

    def _validate_configured_dimensions(
        self,
        vectors: tuple[tuple[float, ...], ...],
    ) -> None:
        if self._dimensions is not None and vectors and len(vectors[0]) != self._dimensions:
            raise ValueError("embedding response dimensions do not match configuration")
