import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from researchflow.app_factory import create_app
from researchflow.core.config import Settings
from researchflow.integrations.llm.fake import FakeLLMClient
from researchflow.integrations.web.fake import FakeSearchProvider, FakeWebPageReader


async def test_default_cors_accepts_both_local_frontend_hosts(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'cors.db').as_posix()}",
            simulation_step_delay=0,
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            response = await client.options(
                "/api/research-runs",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert response.headers["access-control-allow-credentials"] == "true"


async def test_optional_demo_access_code_protects_api_with_http_only_cookie(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'access.db').as_posix()}",
            demo_access_code="portfolio-secret",
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            blocked = await client.get("/api/research-runs")
            invalid = await client.post("/api/demo-session", json={"access_code": "wrong"})
            unlocked = await client.post(
                "/api/demo-session", json={"access_code": "portfolio-secret"}
            )
            allowed = await client.get("/api/research-runs")

    assert blocked.status_code == 401
    assert blocked.json()["code"] == "DEMO_ACCESS_REQUIRED"
    assert invalid.status_code == 401
    assert unlocked.status_code == 204
    cookie = unlocked.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "portfolio-secret" not in unlocked.headers["set-cookie"]
    assert allowed.status_code == 200


async def test_production_demo_cookie_supports_separate_web_and_api_origins(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="production",
            workflow_mode="langgraph",
            llm_model="model",
            cors_origins=("https://web.example.com",),
            demo_access_code="long-demo-secret",
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'production.db').as_posix()}",
        ),
        llm_client=FakeLLMClient(),
        search_provider=FakeSearchProvider(),
        page_reader=FakeWebPageReader(),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://api.example.com") as client:
        response = await client.post("/api/demo-session", json={"access_code": "long-demo-secret"})

    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie
    assert "samesite=none" in cookie


async def test_research_run_completes_and_persists(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            simulation_step_delay=0.01,
        )
    )

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/research-runs",
                json={"goal": "调研 AI 代码生成工具的评测方案和现有学术基准"},
            )
            assert response.status_code == 201
            run_id = response.json()["id"]

            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)

            payload = detail.json()
            assert payload["status"] == "completed"
            assert payload["progress"] == 100
            assert "模拟结果" in payload["report_markdown"]

            history = await client.get("/api/research-runs")
            assert history.status_code == 200
            assert history.json()["items"][0]["id"] == run_id


async def test_short_goal_is_rejected(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
            simulation_step_delay=0,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/research-runs", json={"goal": "太短"})
            assert response.status_code == 422


async def test_blank_goal_uses_stable_validation_error(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'blank.db').as_posix()}",
            simulation_step_delay=0,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/research-runs", json={"goal": "          "})

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": "请求数据不符合要求",
        "details": [
            {
                "field": "goal",
                "message": "研究目标至少需要 10 个字符",
            }
        ],
    }


async def test_missing_run_uses_stable_not_found_error(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'missing.db').as_posix()}",
            simulation_step_delay=0,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research-runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {
        "code": "RUN_NOT_FOUND",
        "message": "研究运行不存在",
        "details": None,
    }
