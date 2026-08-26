import json

import httpx
import pytest

from researchflow.integrations.embedding.base import EmbeddingClientError, EmbeddingTask
from researchflow.integrations.embedding.gemini import GeminiEmbeddingClient
from researchflow.integrations.embedding.openai_compatible import (
    OpenAICompatibleEmbeddingClient,
)


async def test_openai_compatible_embedding_batches_and_restores_index_order() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        data = [
            {"object": "embedding", "index": index, "embedding": [float(index), 1.0]}
            for index in reversed(range(len(body["input"])))
        ]
        return httpx.Response(200, json={"object": "list", "data": data})

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://embedding.example/v1",
        model="embedding-model",
        api_key="secret",
        timeout_seconds=5,
        dimensions=2,
        batch_size=2,
        transport=httpx.MockTransport(handler),
    )

    vectors = await client.embed(
        ("first", "second", "third"),
        task=EmbeddingTask.DOCUMENT,
    )

    assert vectors == ((0.0, 1.0), (1.0, 1.0), (0.0, 1.0))
    assert [request["input"] for request in requests] == [["first", "second"], ["third"]]
    assert all(request["dimensions"] == 2 for request in requests)
    assert all(request["encoding_format"] == "float" for request in requests)


async def test_openai_compatible_embedding_rejects_invalid_dimensions() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [1.0, 0.0]},
                    {"index": 1, "embedding": [1.0]},
                ]
            },
        )

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://embedding.example/v1",
        model="embedding-model",
        api_key=None,
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingClientError) as captured:
        await client.embed(("first", "second"), task=EmbeddingTask.QUERY)

    assert captured.value.code == "EMBEDDING_INVALID_RESPONSE"


async def test_gemini_embedding_2_uses_search_instructions_and_native_batch() -> None:
    requests: list[tuple[httpx.Request, dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append((request, body))
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    {"values": [float(index), 1.0]} for index in range(len(body["requests"]))
                ]
            },
        )

    client = GeminiEmbeddingClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-embedding-2",
        api_key="gemini-secret",
        timeout_seconds=5,
        dimensions=2,
        batch_size=2,
        transport=httpx.MockTransport(handler),
    )

    vectors = await client.embed(("doc one", "doc two"), task=EmbeddingTask.DOCUMENT)

    assert vectors == ((0.0, 1.0), (1.0, 1.0))
    request, body = requests[0]
    assert request.url.path.endswith("/models/gemini-embedding-2:batchEmbedContents")
    assert request.headers["x-goog-api-key"] == "gemini-secret"
    assert all(
        item["embedContentConfig"] == {"outputDimensionality": 2}
        for item in body["requests"]
    )
    assert [item["content"]["parts"][0]["text"] for item in body["requests"]] == [
        "title: none | text: doc one",
        "title: none | text: doc two",
    ]
    assert client.model == "gemini:gemini-embedding-2:2:search-prefix-v1"

    await client.embed(("query",), task=EmbeddingTask.QUERY)
    query_request = requests[1][1]["requests"][0]
    assert query_request["content"]["parts"][0]["text"] == "task: search result | query: query"
    assert "taskType" not in query_request["embedContentConfig"]


async def test_gemini_embedding_1_uses_retrieval_task_types() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={"embeddings": [{"values": [1.0, 0.0]}]})

    client = GeminiEmbeddingClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-embedding-001",
        api_key="gemini-secret",
        timeout_seconds=5,
        dimensions=2,
        transport=httpx.MockTransport(handler),
    )

    await client.embed(("document",), task=EmbeddingTask.DOCUMENT)
    await client.embed(("query",), task=EmbeddingTask.QUERY)

    assert requests[0]["requests"][0]["embedContentConfig"]["taskType"] == "RETRIEVAL_DOCUMENT"
    assert requests[1]["requests"][0]["embedContentConfig"]["taskType"] == "RETRIEVAL_QUERY"
    assert client.model == "gemini:gemini-embedding-001:2:task-type-v1"
