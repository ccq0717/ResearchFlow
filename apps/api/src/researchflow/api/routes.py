import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from researchflow.api.schemas import (
    ArchiveResearchRunRequest,
    CreateResearchRunRequest,
    DemoSessionRequest,
    DocumentChunkListResponse,
    DocumentChunkResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    RenameResearchRunRequest,
    ResearchEventListResponse,
    ResearchEventResponse,
    ResearchMaterialsResponse,
    ResearchPlanEnvelope,
    ResearchPlanResponse,
    ResearchRunListResponse,
    ResearchRunMetricsResponse,
    ResearchRunResponse,
)
from researchflow.application.knowledge_library import KnowledgeLibrary, KnowledgeLibraryError
from researchflow.application.research_runs import (
    ResearchRunApplication,
    ResearchRunApplicationError,
)
from researchflow.domain.research import ResearchEvent

router = APIRouter(prefix="/api")


@router.post("/demo-session", status_code=status.HTTP_204_NO_CONTENT)
async def create_demo_session(body: DemoSessionRequest, request: Request) -> Response:
    guard = request.app.state.demo_access_guard
    if not guard.authenticate(body.access_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_ACCESS_CODE", "message": "访问码无效"},
        )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.set_cookie(
        guard.cookie_name,
        guard.issue_session(),
        httponly=True,
        secure=guard.secure_cookie,
        samesite=guard.cookie_same_site,
        max_age=guard.session_ttl_seconds,
    )
    return response


@router.delete("/demo-session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demo_session(request: Request) -> Response:
    guard = request.app.state.demo_access_guard
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(guard.cookie_name)
    return response


def _application(request: Request) -> ResearchRunApplication:
    return request.app.state.research_runs


def _knowledge_library(request: Request) -> KnowledgeLibrary:
    return request.app.state.knowledge_library


def _knowledge_error(error: KnowledgeLibraryError) -> HTTPException:
    status_code = {
        "KNOWLEDGE_DOCUMENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "KNOWLEDGE_DOCUMENT_DUPLICATE": status.HTTP_409_CONFLICT,
        "KNOWLEDGE_DOCUMENT_LIMIT_REACHED": status.HTTP_409_CONFLICT,
        "DOCUMENT_TOO_LARGE": status.HTTP_413_CONTENT_TOO_LARGE,
    }.get(error.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.public_message},
    )


def _run_error(error: ResearchRunApplicationError) -> HTTPException:
    status_code = {
        "RUN_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "RUN_CAPACITY_REACHED": status.HTTP_429_TOO_MANY_REQUESTS,
        "DAILY_RUN_LIMIT_REACHED": status.HTTP_429_TOO_MANY_REQUESTS,
    }.get(error.code, status.HTTP_409_CONFLICT)
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.public_message},
    )


@router.post(
    "/knowledge-documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_document(
    file: Annotated[UploadFile, File(description="PDF、Markdown 或 UTF-8 纯文本")],
    request: Request,
) -> KnowledgeDocumentResponse:
    library = _knowledge_library(request)
    try:
        data = await file.read(library.max_document_bytes + 1)
    finally:
        await file.close()
    try:
        document = await library.upload(file.filename, data)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    return KnowledgeDocumentResponse.from_domain(document)


@router.get("/knowledge-documents", response_model=KnowledgeDocumentListResponse)
async def list_knowledge_documents(request: Request) -> KnowledgeDocumentListResponse:
    documents = await _knowledge_library(request).list_documents()
    return KnowledgeDocumentListResponse(
        items=[KnowledgeDocumentResponse.from_domain(document) for document in documents]
    )


@router.get("/knowledge-documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_knowledge_document(
    document_id: UUID,
    request: Request,
) -> KnowledgeDocumentResponse:
    document = await _knowledge_library(request).get(document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "KNOWLEDGE_DOCUMENT_NOT_FOUND"},
        )
    return KnowledgeDocumentResponse.from_domain(document)


@router.get(
    "/knowledge-documents/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
)
async def list_knowledge_document_chunks(
    document_id: UUID,
    request: Request,
) -> DocumentChunkListResponse:
    try:
        chunks = await _knowledge_library(request).list_chunks(document_id)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    return DocumentChunkListResponse(
        items=[DocumentChunkResponse.from_domain(chunk) for chunk in chunks]
    )


@router.get("/knowledge-documents/{document_id}/content")
async def get_knowledge_document_content(document_id: UUID, request: Request) -> Response:
    try:
        document, content = await _knowledge_library(request).read_content(document_id)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    encoded_filename = quote(document.original_filename)
    return Response(
        content=content,
        media_type=document.media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"},
    )


@router.post(
    "/knowledge-documents/{document_id}/reprocess",
    response_model=KnowledgeDocumentResponse,
)
async def reprocess_knowledge_document(
    document_id: UUID,
    request: Request,
) -> KnowledgeDocumentResponse:
    try:
        document = await _knowledge_library(request).reprocess(document_id)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    return KnowledgeDocumentResponse.from_domain(document)


@router.delete(
    "/knowledge-documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_knowledge_document(document_id: UUID, request: Request) -> Response:
    try:
        await _knowledge_library(request).delete(document_id)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/research-runs",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_run(
    body: CreateResearchRunRequest, request: Request
) -> ResearchRunResponse:
    try:
        run = await _application(request).create_run(body.goal, body.document_ids)
    except KnowledgeLibraryError as error:
        raise _knowledge_error(error) from error
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return ResearchRunResponse.from_domain(run)


@router.get("/research-runs", response_model=ResearchRunListResponse)
async def list_research_runs(
    request: Request, include_archived: bool = False
) -> ResearchRunListResponse:
    runs = await _application(request).list_runs(include_archived=include_archived)
    return ResearchRunListResponse(items=[ResearchRunResponse.from_domain(run) for run in runs])


@router.get("/research-runs/{run_id}", response_model=ResearchRunResponse)
async def get_research_run(run_id: UUID, request: Request) -> ResearchRunResponse:
    run = await _application(request).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})
    return ResearchRunResponse.from_domain(run)


@router.get("/research-runs/{run_id}/metrics", response_model=ResearchRunMetricsResponse)
async def get_research_run_metrics(run_id: UUID, request: Request) -> ResearchRunMetricsResponse:
    try:
        metrics = await _application(request).get_metrics(run_id)
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return ResearchRunMetricsResponse.from_domain(metrics)


@router.post(
    "/research-runs/{run_id}/cancel",
    response_model=ResearchRunResponse,
)
async def cancel_research_run(run_id: UUID, request: Request) -> ResearchRunResponse:
    try:
        run = await _application(request).cancel_run(run_id)
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return ResearchRunResponse.from_domain(run)


@router.post("/research-runs/{run_id}/retry", response_model=ResearchRunResponse)
async def retry_research_run(run_id: UUID, request: Request) -> ResearchRunResponse:
    try:
        run = await _application(request).retry_run(run_id)
    except (ResearchRunApplicationError, KnowledgeLibraryError) as error:
        if isinstance(error, KnowledgeLibraryError):
            raise _knowledge_error(error) from error
        raise _run_error(error) from error
    return ResearchRunResponse.from_domain(run)


@router.patch("/research-runs/{run_id}", response_model=ResearchRunResponse)
async def rename_research_run(
    run_id: UUID, body: RenameResearchRunRequest, request: Request
) -> ResearchRunResponse:
    try:
        run = await _application(request).rename_run(run_id, body.title)
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return ResearchRunResponse.from_domain(run)


@router.patch("/research-runs/{run_id}/archive", response_model=ResearchRunResponse)
async def archive_research_run(
    run_id: UUID, body: ArchiveResearchRunRequest, request: Request
) -> ResearchRunResponse:
    try:
        run = await _application(request).archive_run(run_id, body.archived)
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return ResearchRunResponse.from_domain(run)


@router.delete("/research-runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_run(run_id: UUID, request: Request) -> Response:
    try:
        await _application(request).delete_run(run_id)
    except ResearchRunApplicationError as error:
        raise _run_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/research-runs/{run_id}/plan", response_model=ResearchPlanEnvelope)
async def get_research_plan(run_id: UUID, request: Request) -> ResearchPlanEnvelope:
    application = _application(request)
    if await application.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})
    plan = await application.get_plan(run_id)
    return ResearchPlanEnvelope(
        plan=ResearchPlanResponse.from_domain(plan) if plan is not None else None
    )


@router.get(
    "/research-runs/{run_id}/materials",
    response_model=ResearchMaterialsResponse,
)
async def get_research_materials(
    run_id: UUID,
    request: Request,
) -> ResearchMaterialsResponse:
    application = _application(request)
    if await application.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})
    return ResearchMaterialsResponse.from_domain(await application.get_materials(run_id))


@router.get(
    "/research-runs/{run_id}/events/history",
    response_model=ResearchEventListResponse,
)
async def list_research_events(run_id: UUID, request: Request) -> ResearchEventListResponse:
    application = _application(request)
    if await application.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})
    events = await application.list_events(run_id)
    return ResearchEventListResponse(
        items=[ResearchEventResponse.from_domain(event) for event in events]
    )


@router.get("/research-runs/{run_id}/events")
async def stream_research_events(
    run_id: UUID,
    request: Request,
    last_event_id: int | None = Header(default=None, alias="Last-Event-ID"),
    after: int = 0,
) -> StreamingResponse:
    application = _application(request)
    run = await application.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})

    async def generate() -> AsyncIterator[str]:
        sequence = max(last_event_id or 0, after)
        yield _format_sse(
            event_type="stream.ready",
            data={
                "sequence": sequence,
                "run_id": str(run_id),
                "type": "stream.ready",
                "stage": run.current_stage,
                "message": "事件流已连接",
                "progress": run.progress,
                "created_at": run.updated_at.isoformat(),
                "payload": {"status": run.status},
            },
        )
        idle_cycles = 0
        while not await request.is_disconnected():
            # 先读取状态、再读取事件。若状态已终结，对应终结事件已经在同一事务中提交，
            # 因此随后的事件查询一定能补齐终结事件后再关闭连接。
            current = await application.get_run(run_id)
            events = await application.events_after(run_id, sequence)
            for event in events:
                sequence = event.sequence
                yield _format_event(event)
            if current is None or current.status.is_terminal:
                return
            if not events:
                idle_cycles += 1
                if idle_cycles >= 15:
                    idle_cycles = 0
                    yield ": heartbeat\n\n"
            else:
                idle_cycles = 0
            await asyncio.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _format_event(event: ResearchEvent) -> str:
    return _format_sse(
        event_id=event.sequence,
        event_type="research.event",
        data={
            "sequence": event.sequence,
            "run_id": str(event.run_id),
            "type": event.type,
            "stage": event.stage,
            "message": event.message,
            "progress": event.progress,
            "created_at": event.created_at.isoformat(),
            "payload": event.payload or {},
        },
    )


def _format_sse(*, event_type: str, data: dict[str, object], event_id: int | None = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False, default=str)}")
    return "\n".join(lines) + "\n\n"
