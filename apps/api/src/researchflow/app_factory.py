import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from researchflow.api.errors import register_error_handlers
from researchflow.api.routes import router
from researchflow.application.knowledge_library import KnowledgeLibrary
from researchflow.application.research_runs import ResearchRunApplication
from researchflow.core.access import DemoAccessGuard
from researchflow.core.config import Settings, get_settings
from researchflow.ingestion.retrieval import EmbeddingKnowledgeRetriever
from researchflow.integrations.embedding.base import EmbeddingClient, UnconfiguredEmbeddingClient
from researchflow.integrations.embedding.gemini import GeminiEmbeddingClient
from researchflow.integrations.embedding.openai_compatible import OpenAICompatibleEmbeddingClient
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
from researchflow.persistence.knowledge_repository import SqliteKnowledgeRepository
from researchflow.persistence.repository import SqliteResearchRepository
from researchflow.workflows.langgraph_research import LangGraphResearchWorkflow
from researchflow.workflows.llm_research import LLMResearchWorkflow
from researchflow.workflows.simulated import SimulatedResearchWorkflow

logger = logging.getLogger("researchflow.http")


def create_app(
    settings: Settings | None = None,
    *,
    llm_client: LLMClient | None = None,
    embedding_client: EmbeddingClient | None = None,
    search_provider: SearchProvider | None = None,
    page_reader: WebPageReader | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.ensure_runtime_directories()
    engine = create_engine(resolved_settings.database_url)
    session_factory = create_session_factory(engine)
    repository = SqliteResearchRepository(session_factory)
    knowledge_repository = SqliteKnowledgeRepository(session_factory)
    if embedding_client is not None:
        resolved_embedding = embedding_client
    elif resolved_settings.embedding_model.strip():
        if resolved_settings.embedding_provider == "gemini":
            if resolved_settings.embedding_api_key is None:
                raise ValueError("Gemini Embedding 必须设置 RESEARCHFLOW_EMBEDDING_API_KEY")
            embedding_api_key = resolved_settings.embedding_api_key.get_secret_value().strip()
            if not embedding_api_key:
                raise ValueError("Gemini Embedding 必须设置 RESEARCHFLOW_EMBEDDING_API_KEY")
            resolved_embedding = GeminiEmbeddingClient(
                base_url=str(resolved_settings.embedding_base_url),
                model=resolved_settings.embedding_model,
                api_key=embedding_api_key,
                timeout_seconds=resolved_settings.embedding_timeout_seconds,
                dimensions=resolved_settings.embedding_dimensions,
                batch_size=resolved_settings.embedding_batch_size,
            )
        elif resolved_settings.embedding_provider == "openai-compatible":
            resolved_embedding = OpenAICompatibleEmbeddingClient(
                base_url=str(resolved_settings.embedding_base_url),
                model=resolved_settings.embedding_model,
                api_key=(
                    resolved_settings.embedding_api_key.get_secret_value()
                    if resolved_settings.embedding_api_key is not None
                    else None
                ),
                timeout_seconds=resolved_settings.embedding_timeout_seconds,
                dimensions=resolved_settings.embedding_dimensions,
                batch_size=resolved_settings.embedding_batch_size,
            )
        else:
            raise ValueError(f"不支持的 Embedding Provider：{resolved_settings.embedding_provider}")
    else:
        resolved_embedding = UnconfiguredEmbeddingClient()
    knowledge_library = KnowledgeLibrary(
        knowledge_repository,
        embedding_client=resolved_embedding,
        upload_directory=resolved_settings.knowledge_upload_directory,
        max_document_bytes=resolved_settings.knowledge_max_document_bytes,
        max_document_count=resolved_settings.knowledge_max_document_count,
        max_selection_count=resolved_settings.knowledge_max_selection_count,
        chunk_size=resolved_settings.knowledge_chunk_size,
        max_extracted_characters=resolved_settings.knowledge_max_extracted_characters,
        max_pdf_pages=resolved_settings.knowledge_max_pdf_pages,
        max_pdf_page_stream_bytes=resolved_settings.knowledge_max_pdf_page_stream_bytes,
    )
    knowledge_retriever = EmbeddingKnowledgeRetriever(
        knowledge_repository,
        embedding_client=resolved_embedding,
    )

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
            knowledge_retriever=knowledge_retriever,
            knowledge_results_per_question=resolved_settings.knowledge_results_per_question,
        )
    elif resolved_settings.workflow_mode == "llm":
        workflow = LLMResearchWorkflow(client, resolved_settings.simulation_step_delay)
    else:
        workflow = SimulatedResearchWorkflow(resolved_settings.simulation_step_delay)

    application = ResearchRunApplication(
        repository,
        workflow,
        knowledge_library,
        llm_input_cost_per_million_tokens=(resolved_settings.llm_input_cost_per_million_tokens),
        llm_output_cost_per_million_tokens=(resolved_settings.llm_output_cost_per_million_tokens),
        max_concurrent_runs=resolved_settings.max_concurrent_runs,
        max_runs_per_day=resolved_settings.max_runs_per_day,
    )

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
    app.state.knowledge_library = knowledge_library
    access_code = (
        resolved_settings.demo_access_code.get_secret_value().strip()
        if resolved_settings.demo_access_code is not None
        else None
    ) or None
    app.state.demo_access_guard = DemoAccessGuard(
        access_code,
        secure_cookie=resolved_settings.environment == "production",
    )

    @app.middleware("http")
    async def protect_demo(request, call_next):
        guard = request.app.state.demo_access_guard
        public_path = request.url.path in {"/health", "/api/demo-session"}
        if (
            guard.enabled
            and request.method != "OPTIONS"
            and request.url.path.startswith("/api")
            and not public_path
            and not guard.allows(request.cookies.get(guard.cookie_name))
        ):
            return JSONResponse(
                status_code=401,
                content={"code": "DEMO_ACCESS_REQUIRED", "message": "请输入演示访问码"},
            )
        return await call_next(request)

    @app.middleware("http")
    async def log_request(request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:100]
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                "request.completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000),
                },
            )

    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
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
