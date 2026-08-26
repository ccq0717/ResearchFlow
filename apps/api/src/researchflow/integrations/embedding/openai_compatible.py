import json
import math
from typing import Any

import httpx

from researchflow.integrations.embedding.base import EmbeddingClientError, EmbeddingTask


class OpenAICompatibleEmbeddingClient:
    """通过 OpenAI-compatible /embeddings 批量生成浮点向量。"""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: float,
        dimensions: int | None = None,
        batch_size: int = 32,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/embeddings"
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._transport = transport

    @property
    def model(self) -> str:
        dimensions = self._dimensions if self._dimensions is not None else "default"
        return f"openai-compatible:{self._model}:{dimensions}"

    async def embed(
        self,
        texts: tuple[str, ...],
        *,
        task: EmbeddingTask,
    ) -> tuple[tuple[float, ...], ...]:
        del task
        if not texts:
            return ()
        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(await self._embed_batch(texts[start : start + self._batch_size]))
        return tuple(vectors)

    async def _embed_batch(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        body: dict[str, Any] = {
            "model": self._model,
            "input": list(texts),
            "encoding_format": "float",
        }
        if self._dimensions is not None:
            body["dimensions"] = self._dimensions
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(self._endpoint, headers=headers, json=body)
                response.raise_for_status()
            vectors = self._parse_vectors(response.json(), len(texts))
            self._validate_configured_dimensions(vectors)
            return vectors
        except httpx.TimeoutException as error:
            raise EmbeddingClientError(
                "EMBEDDING_TIMEOUT", "Embedding 服务响应超时，请稍后重试"
            ) from error
        except httpx.HTTPStatusError as error:
            raise EmbeddingClientError(
                "EMBEDDING_HTTP_ERROR",
                f"Embedding 服务返回错误状态（HTTP {error.response.status_code}）",
            ) from error
        except httpx.RequestError as error:
            raise EmbeddingClientError(
                "EMBEDDING_CONNECTION_ERROR", "无法连接 Embedding 服务"
            ) from error
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise EmbeddingClientError(
                "EMBEDDING_INVALID_RESPONSE", "Embedding 服务返回的数据格式无效"
            ) from error

    @staticmethod
    def _parse_vectors(payload: object, expected_count: int) -> tuple[tuple[float, ...], ...]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise TypeError("data must be a list")
        indexed: dict[int, tuple[float, ...]] = {}
        dimensions: int | None = None
        for item in payload["data"]:
            if not isinstance(item, dict):
                raise TypeError("embedding item must be an object")
            index = item.get("index")
            raw_vector = item.get("embedding")
            if not isinstance(index, int) or not isinstance(raw_vector, list) or not raw_vector:
                raise TypeError("invalid embedding item")
            vector = tuple(float(value) for value in raw_vector)
            if not all(math.isfinite(value) for value in vector):
                raise ValueError("embedding contains non-finite values")
            dimensions = dimensions or len(vector)
            if len(vector) != dimensions or index in indexed:
                raise ValueError("embedding dimensions or indexes are inconsistent")
            indexed[index] = vector
        if set(indexed) != set(range(expected_count)):
            raise ValueError("embedding response count does not match input")
        return tuple(indexed[index] for index in range(expected_count))

    def _validate_configured_dimensions(
        self,
        vectors: tuple[tuple[float, ...], ...],
    ) -> None:
        if self._dimensions is not None and vectors and len(vectors[0]) != self._dimensions:
            raise ValueError("embedding response dimensions do not match configuration")
