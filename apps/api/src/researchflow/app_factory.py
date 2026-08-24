from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from researchflow.api.errors import register_error_handlers
from researchflow.api.routes import router
from researchflow.application.research_runs import ResearchRunApplication
from researchflow.core.config import Settings, get_settings
from researchflow.integrations.llm.base import LLMClient
from researchflow.integrations.llm.openai_compatible import OpenAICompatibleLLMClient
from researchflow.persistence.database import (
    create_engine,
    create_schema,
    create_session_factory,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.llm_research import LLMResearchWorkflow
from researchflow.workflows.simulated import SimulatedResearchWorkflow


def create_app(
    settings: Settings | None = None,
    *,
    llm_client: LLMClient | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.ensure_runtime_directories()
    engine = create_engine(resolved_settings.database_url)
    repository = SqliteResearchRepository(create_session_factory(engine))

    if resolved_settings.workflow_mode == "llm":
        client = llm_client or OpenAICompatibleLLMClient(
            base_url=str(resolved_settings.llm_base_url),
            model=resolved_settings.llm_model,
            api_key=(
                resolved_settings.llm_api_key.get_secret_value()
                if resolved_settings.llm_api_key is not None
                else None
            ),
            timeout_seconds=resolved_settings.llm_timeout_seconds,
            provider=resolved_settings.llm_provider,
        )
        workflow = LLMResearchWorkflow(client, resolved_settings.simulation_step_delay)
    else:
        workflow = SimulatedResearchWorkflow(resolved_settings.simulation_step_delay)

    application = ResearchRunApplication(repository, workflow)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await create_schema(engine)
        await application.recover_interrupted_runs()
        try:
            yield
        finally:
            try:
                await application.shutdown()
            finally:
                await engine.dispose()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.research_runs = application
    register_error_handlers(app)
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
        return {
            "status": "ok",
            "workflow_mode": resolved_settings.workflow_mode,
        }

    return app
