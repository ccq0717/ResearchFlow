import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from researchflow.app_factory import create_app
from researchflow.core.config import Settings
from researchflow.domain.research import ResearchRun, ResearchRunStatus
from researchflow.persistence.database import (
    create_engine,
    create_schema,
    create_session_factory,
)
from researchflow.persistence.repository import SqliteResearchRepository


def _settings(database_path: Path, *, step_delay: float = 0) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        workflow_mode="simulation",
        simulation_step_delay=step_delay,
    )


async def test_sse_stream_contains_terminal_events(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path / "sse.db"))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "验证研究任务完成时 SSE 可以收到完整终态事件"},
            )
            run_id = created.json()["id"]

            async with client.stream("GET", f"/api/research-runs/{run_id}/events") as response:
                body = (await response.aread()).decode("utf-8")

            assert response.status_code == 200
            assert body.count("event: research.event") >= 2
            assert '"type": "report.completed"' in body
            assert '"type": "run.completed"' in body


async def test_event_history_survives_reopen_and_keeps_utc_offset(tmp_path: Path) -> None:
    database_path = tmp_path / "event-history.db"
    app = create_app(_settings(database_path))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "验证重新打开研究记录后可以恢复完整事件历史"},
            )
            run_id = created.json()["id"]
            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)

    reopened = create_app(_settings(database_path))
    async with reopened.router.lifespan_context(reopened):
        async with AsyncClient(
            transport=ASGITransport(app=reopened),
            base_url="http://test",
        ) as client:
            history = await client.get(f"/api/research-runs/{run_id}/events/history")
            items = history.json()["items"]

            assert history.status_code == 200
            assert items[0]["type"] == "run.queued"
            assert items[-1]["type"] == "run.completed"
            assert all(item["created_at"].endswith(("Z", "+00:00")) for item in items)


async def test_shutdown_marks_active_run_as_interrupted(tmp_path: Path) -> None:
    database_path = tmp_path / "shutdown.db"
    app = create_app(_settings(database_path, step_delay=10))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "验证关闭后端时运行中的研究任务会被安全终结"},
            )
            run_id = created.json()["id"]
            for _ in range(50):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "running":
                    break
                await asyncio.sleep(0.01)

    reopened = create_app(_settings(database_path))
    async with reopened.router.lifespan_context(reopened):
        async with AsyncClient(
            transport=ASGITransport(app=reopened),
            base_url="http://test",
        ) as client:
            detail = await client.get(f"/api/research-runs/{run_id}")
            payload = detail.json()
            assert payload["status"] == "failed"
            assert payload["error_code"] == "RUN_INTERRUPTED"


async def test_startup_recovers_orphaned_run(tmp_path: Path) -> None:
    database_path = tmp_path / "recovery.db"
    settings = _settings(database_path)
    engine = create_engine(settings.database_url)
    await create_schema(engine)
    repository = SqliteResearchRepository(create_session_factory(engine))
    now = datetime.now(UTC)
    run = ResearchRun(
        id=uuid4(),
        goal="验证异常退出后遗留的运行状态可以在重启时恢复",
        title="验证异常退出恢复",
        status=ResearchRunStatus.RUNNING,
        current_stage=None,
        progress=20,
        report_markdown=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
    )
    await repository.create(run)
    await repository.append_event(
        run.id,
        event_type="run.started",
        message="研究工作流开始执行",
        progress=20,
    )
    await engine.dispose()

    app = create_app(settings)
    async with app.router.lifespan_context(app):
        recovered = await app.state.research_runs.get_run(UUID(str(run.id)))
        events = await app.state.research_runs.list_events(run.id)

    assert recovered is not None
    assert recovered.status == ResearchRunStatus.FAILED
    assert recovered.error_code == "RUN_INTERRUPTED"
    assert events[-1].type == "run.failed"
