from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from researchflow.api.routes import router
from researchflow.application.research_runs import ResearchRunApplication
from researchflow.core.config import Settings, get_settings
from researchflow.persistence.database import (
    create_engine,
    create_schema,
    create_session_factory,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.simulated import SimulatedResearchWorkflow


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.ensure_runtime_directories()
    engine = create_engine(resolved_settings.database_url)
    repository = SqliteResearchRepository(create_session_factory(engine))
    workflow = SimulatedResearchWorkflow(repository, resolved_settings.simulation_step_delay)
    application = ResearchRunApplication(repository, workflow)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await create_schema(engine)
        yield
        await engine.dispose()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.research_runs = application
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
