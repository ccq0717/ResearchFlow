import asyncio
import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from researchflow.app_factory import create_app
from researchflow.core.config import Settings
from researchflow.integrations.llm.fake import FakeLLMClient
from researchflow.integrations.web.base import SearchResult, WebResearchError
from researchflow.integrations.web.exa import ExaSearchProvider
from researchflow.integrations.web.fake import FakeSearchProvider, FakeWebPageReader
from researchflow.integrations.web.result_reader import SearchResultPageReader


def _settings(database_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        workflow_mode="langgraph",
        llm_model="fake-model",
        web_search_result_limit=2,
    )


async def test_langgraph_web_research_persists_materials_and_report(tmp_path: Path) -> None:
    database_path = tmp_path / "langgraph.db"
    app = create_app(
        _settings(database_path),
        llm_client=FakeLLMClient(),
        search_provider=FakeSearchProvider(),
        page_reader=FakeWebPageReader(),
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "调研 AI 代码生成工具的评测方法并形成带网页来源的方案"},
            )
            run_id = created.json()["id"]
            detail = created
            for _ in range(200):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] in {"completed", "failed"}:
                    break
                await asyncio.sleep(0.01)

            assert detail.json()["status"] == "completed", detail.json()
            assert "M2 网页研究" in detail.json()["report_markdown"]
            assert "https://example.test/" in detail.json()["report_markdown"]

            materials_response = await client.get(f"/api/research-runs/{run_id}/materials")
            materials = materials_response.json()
            assert materials_response.status_code == 200
            assert len(materials["tasks"]) == 3
            assert len(materials["sources"]) == 6
            assert len(materials["evidence"]) == 6
            assert {item["status"] for item in materials["tasks"]} == {"completed"}
            assert {item["query"] for item in materials["tasks"]} == {
                "AI code generation evaluation metrics",
                "code generation benchmark dataset",
                "automated code evaluation human review",
            }
            assert all(item["source_id"].startswith("s") for item in materials["evidence"])

            plan = (await client.get(f"/api/research-runs/{run_id}/plan")).json()["plan"]
            assert all(question["search_query"] for question in plan["questions"])

            events = (await client.get(f"/api/research-runs/{run_id}/events/history")).json()[
                "items"
            ]
            event_types = {event["type"] for event in events}
            assert {
                "research.plan.completed",
                "research.tasks.completed",
                "research.sources.completed",
                "research.evidence.completed",
                "report.completed",
                "run.completed",
            } <= event_types

    reopened = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        )
    )
    async with reopened.router.lifespan_context(reopened):
        async with AsyncClient(
            transport=ASGITransport(app=reopened),
            base_url="http://test",
        ) as client:
            materials = (await client.get(f"/api/research-runs/{run_id}/materials")).json()
            assert len(materials["sources"]) == 6
            assert len(materials["evidence"]) == 6


async def test_exa_search_and_reader_parse_external_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.exa.ai/search"
        assert request.headers["x-api-key"] == "test-exa-key"
        assert json.loads(request.content) == {
            "query": "code generation evaluation",
            "type": "auto",
            "numResults": 2,
            "contents": {"highlights": True},
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Evaluating AI-generated code",
                        "url": "https://example.org/research/code-evaluation",
                        "author": "Research Team",
                        "publishedDate": "2026-07-01T00:00:00.000Z",
                        "highlights": [
                            "Use reproducible tests and security checks.",
                            "Combine automated metrics with human review.",
                        ],
                    }
                ]
            },
        )

    search = ExaSearchProvider(
        base_url="https://api.exa.ai",
        api_key="test-exa-key",
        timeout_seconds=5,
        user_agent="ResearchFlow tests",
        transport=httpx.MockTransport(handler),
    )
    results = await search.search("code generation evaluation", limit=2)
    assert results == (
        SearchResult(
            title="Evaluating AI-generated code",
            url="https://example.org/research/code-evaluation",
            snippet=(
                "Use reproducible tests and security checks.\n\n"
                "Combine automated metrics with human review."
            ),
            content=(
                "Use reproducible tests and security checks.\n\n"
                "Combine automated metrics with human review."
            ),
            published_at="2026-07-01T00:00:00.000Z",
            author="Research Team",
        ),
    )

    reader = SearchResultPageReader(max_characters=2000)
    document = await reader.read(results[0])
    assert document.title == "Evaluating AI-generated code"
    assert document.url == "https://example.org/research/code-evaluation"
    assert document.content == results[0].content


async def test_exa_retries_a_transient_failure_once() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Retry succeeded",
                        "url": "https://example.org/retry",
                        "highlights": ["The retry returned a usable result."],
                    }
                ]
            },
        )

    provider = ExaSearchProvider(
        base_url="https://api.exa.ai",
        api_key="test-exa-key",
        timeout_seconds=5,
        user_agent="ResearchFlow tests",
        transport=httpx.MockTransport(handler),
    )

    results = await provider.search("retry behavior", limit=1)

    assert calls == 2
    assert results[0].title == "Retry succeeded"


async def test_exa_maps_authentication_failure_without_leaking_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    provider = ExaSearchProvider(
        base_url="https://api.exa.ai",
        api_key="secret-that-must-not-leak",
        timeout_seconds=5,
        user_agent="ResearchFlow tests",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(WebResearchError) as captured:
        await provider.search("authentication failure", limit=1)

    assert captured.value.code == "WEB_PROVIDER_AUTH_FAILED"
    assert "secret-that-must-not-leak" not in captured.value.public_message


async def test_search_result_reader_rejects_missing_content() -> None:
    reader = SearchResultPageReader(max_characters=2000)

    with pytest.raises(WebResearchError) as captured:
        await reader.read(
            SearchResult(
                title="Metadata-only result",
                url="https://example.org/metadata",
                snippet="",
            )
        )

    assert captured.value.code == "WEB_CONTENT_UNAVAILABLE"
