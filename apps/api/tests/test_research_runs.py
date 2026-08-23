import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from researchflow.core.config import Settings
from researchflow.main import create_app


async def test_research_run_completes_and_persists(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    app = create_app(
        Settings(
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
            database_url=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
            simulation_step_delay=0,
        )
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/research-runs", json={"goal": "太短"})
            assert response.status_code == 422
