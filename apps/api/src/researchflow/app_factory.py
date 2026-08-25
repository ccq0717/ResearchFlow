from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from researchflow.api.errors import register_error_handlers
from researchflow.api.routes import router
from researchflow.application.research_runs import ResearchRunApplication
from researchflow.core.config import Settings, get_settings
from researchflow.integrations.llm.base import LLMClient
from researchflow.integrations.llm.openai_compatible import OpenAICompatibleLLMClient
from researchflow.integrations.web.base import SearchProvider, WebPageReader
from researchflow.integrations.web.exa import ExaSearchProvider
from researchflow.integrations.web.result_reader import SearchResultPageReader
from researchflow.persistence.database import (
    create_engine,
    create_schema,
    create_session_factory,
)
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.langgraph_research import LangGraphResearchWorkflow
from researchflow.workflows.llm_research import LLMResearchWorkflow
from researchflow.workflows.simulated import SimulatedResearchWorkflow


def create_app(
    settings: Settings | None = None,
    *,
    llm_client: LLMClient | None = None,
    search_provider: SearchProvider | None = None,
    page_reader: WebPageReader | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.ensure_runtime_directories()
    engine = create_engine(resolved_settings.database_url)
    repository = SqliteResearchRepository(create_session_factory(engine))

    if resolved_settings.workflow_mode in {"llm", "langgraph"}:
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
    if resolved_settings.workflow_mode == "langgraph":
        if search_provider is None:
            if resolved_settings.web_search_provider != "exa":
                raise ValueError(
                    f"不支持的网页搜索 Provider：{resolved_settings.web_search_provider}"
                )
            if resolved_settings.web_search_api_key is None:
                raise ValueError("LangGraph 模式必须设置 RESEARCHFLOW_WEB_SEARCH_API_KEY")
            api_key = resolved_settings.web_search_api_key.get_secret_value().strip()
            if not api_key:
                raise ValueError("LangGraph 模式必须设置 RESEARCHFLOW_WEB_SEARCH_API_KEY")
            resolved_search = ExaSearchProvider(
                base_url=str(resolved_settings.web_search_base_url),
                api_key=api_key,
                timeout_seconds=resolved_settings.web_request_timeout_seconds,
                user_agent=resolved_settings.web_user_agent,
            )
        else:
            resolved_search = search_provider
        resolved_reader = page_reader or SearchResultPageReader(
            max_characters=resolved_settings.web_content_max_characters,
        )
        workflow = LangGraphResearchWorkflow(
            llm_client=client,
            search_provider=resolved_search,
            page_reader=resolved_reader,
            results_per_question=resolved_settings.web_search_result_limit,
        )
    elif resolved_settings.workflow_mode == "llm":
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
