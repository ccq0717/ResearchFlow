import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from researchflow.api.schemas import (
    CreateResearchRunRequest,
    ResearchEventListResponse,
    ResearchEventResponse,
    ResearchPlanEnvelope,
    ResearchPlanResponse,
    ResearchRunListResponse,
    ResearchRunResponse,
)
from researchflow.application.research_runs import ResearchRunApplication
from researchflow.domain.research import ResearchEvent

router = APIRouter(prefix="/api")


def _application(request: Request) -> ResearchRunApplication:
    return request.app.state.research_runs


@router.post(
    "/research-runs",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_run(
    body: CreateResearchRunRequest, request: Request
) -> ResearchRunResponse:
    run = await _application(request).create_run(body.goal)
    return ResearchRunResponse.from_domain(run)


@router.get("/research-runs", response_model=ResearchRunListResponse)
async def list_research_runs(request: Request) -> ResearchRunListResponse:
    runs = await _application(request).list_runs()
    return ResearchRunListResponse(items=[ResearchRunResponse.from_domain(run) for run in runs])


@router.get("/research-runs/{run_id}", response_model=ResearchRunResponse)
async def get_research_run(run_id: UUID, request: Request) -> ResearchRunResponse:
    run = await _application(request).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"})
    return ResearchRunResponse.from_domain(run)


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
