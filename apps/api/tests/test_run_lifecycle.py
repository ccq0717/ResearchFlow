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


async def test_restart_marks_active_run_as_interrupted(tmp_path: Path) -> None:
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


async def test_user_can_cancel_an_active_run(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path / "cancel.db", step_delay=10))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "验证用户可以主动取消仍在运行的研究任务"},
            )
            run_id = created.json()["id"]
            for _ in range(50):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "running":
                    break
                await asyncio.sleep(0.01)

            cancelled = await client.post(f"/api/research-runs/{run_id}/cancel")
            payload = cancelled.json()
            history = await client.get(f"/api/research-runs/{run_id}/events/history")

            assert cancelled.status_code == 200
            assert payload["status"] == "cancelled"
            assert payload["completed_at"] is not None
            assert history.json()["items"][-1]["type"] == "run.cancelled"

            repeated = await client.post(f"/api/research-runs/{run_id}/cancel")
            assert repeated.status_code == 409
            assert repeated.json()["code"] == "RUN_NOT_CANCELLABLE"


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


async def test_failed_run_can_be_retried_once_as_a_new_run(tmp_path: Path) -> None:
    database_path = tmp_path / "retry.db"
    settings = _settings(database_path)
    engine = create_engine(settings.database_url)
    await create_schema(engine)
    repository = SqliteResearchRepository(create_session_factory(engine))
    now = datetime.now(UTC)
    failed = ResearchRun(
        id=uuid4(),
        goal="验证失败任务可以保留原记录并创建一次新的研究运行",
        title="验证失败任务重试",
        status=ResearchRunStatus.FAILED,
        current_stage=None,
        progress=30,
        report_markdown=None,
        error_code="RUN_INTERRUPTED",
        error_message="服务曾意外退出",
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
    )
    await repository.create(failed)
    await engine.dispose()

    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/research-runs/{failed.id}/retry")
            assert response.status_code == 200
            retried = response.json()
            assert retried["id"] != str(failed.id)
            assert retried["retry_of"] == str(failed.id)
            assert retried["attempt"] == 2

            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{retried['id']}")
                if detail.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)
            assert detail.json()["status"] == "completed"

            invalid = await client.post(f"/api/research-runs/{retried['id']}/retry")
            assert invalid.status_code == 409
            assert invalid.json()["code"] == "RUN_NOT_RETRYABLE"


async def test_terminal_run_can_be_renamed_archived_and_deleted(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path / "management.db"))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/research-runs",
                json={"goal": "验证研究记录可以重命名归档取消归档并永久删除"},
            )
            run_id = created.json()["id"]
            for _ in range(100):
                detail = await client.get(f"/api/research-runs/{run_id}")
                if detail.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)

            renamed = await client.patch(
                f"/api/research-runs/{run_id}", json={"title": "  新的研究标题  "}
            )
            assert renamed.json()["title"] == "新的研究标题"

            archived = await client.patch(
                f"/api/research-runs/{run_id}/archive", json={"archived": True}
            )
            assert archived.json()["archived"] is True
            assert (await client.get("/api/research-runs")).json()["items"] == []
            assert (
                len((await client.get("/api/research-runs?include_archived=true")).json()["items"])
                == 1
            )

            await client.patch(f"/api/research-runs/{run_id}/archive", json={"archived": False})
            deleted = await client.delete(f"/api/research-runs/{run_id}")
            assert deleted.status_code == 204
            assert (await client.get(f"/api/research-runs/{run_id}")).status_code == 404


async def test_run_creation_enforces_concurrency_and_daily_limits(tmp_path: Path) -> None:
    concurrent_app = create_app(
        _settings(tmp_path / "concurrent.db", step_delay=10).model_copy(
            update={"max_concurrent_runs": 1}
        )
    )
    async with concurrent_app.router.lifespan_context(concurrent_app):
        async with AsyncClient(
            transport=ASGITransport(app=concurrent_app), base_url="http://test"
        ) as client:
            first = await client.post(
                "/api/research-runs", json={"goal": "第一个任务会占用唯一的并发研究名额"}
            )
            second = await client.post(
                "/api/research-runs", json={"goal": "第二个任务应收到明确的容量限制错误"}
            )
            assert first.status_code == 201
            assert second.status_code == 429
            assert second.json()["code"] == "RUN_CAPACITY_REACHED"

    daily_app = create_app(
        _settings(tmp_path / "daily.db").model_copy(update={"max_runs_per_day": 1})
    )
    async with daily_app.router.lifespan_context(daily_app):
        async with AsyncClient(
            transport=ASGITransport(app=daily_app), base_url="http://test"
        ) as client:
            await client.post("/api/research-runs", json={"goal": "今天允许创建的第一项研究任务"})
            limited = await client.post(
                "/api/research-runs", json={"goal": "今天超过持久化配额的第二项研究任务"}
            )
            assert limited.status_code == 429
            assert limited.json()["code"] == "DAILY_RUN_LIMIT_REACHED"
