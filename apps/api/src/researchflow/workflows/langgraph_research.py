from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from researchflow.domain.research import (
    Evidence,
    ResearchEventDraft,
    ResearchPlan,
    ResearchQuestion,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
    ResearchTask,
    ResearchTaskStatus,
    Source,
)
from researchflow.integrations.llm.base import (
    EvidenceDraft,
    LLMClient,
    LLMClientError,
    ResearchDocumentInput,
    ResearchPlanDraft,
    ResearchQuestionDraft,
)
from researchflow.integrations.web.base import (
    SearchProvider,
    SearchResult,
    WebPageReader,
    WebResearchError,
)
from researchflow.workflows.base import ResearchWorkflowUpdate


class _ResearchState(TypedDict, total=False):
    run_id: str
    goal: str
    plan: ResearchPlan
    tasks: tuple[ResearchTask, ...]
    search_results: tuple[tuple[str, SearchResult], ...]
    documents: tuple[ResearchDocumentInput, ...]
    sources: tuple[Source, ...]
    evidence: tuple[Evidence, ...]
    evidence_drafts: tuple[EvidenceDraft, ...]
    report_markdown: str
    warnings: tuple[str, ...]
    check_passed: bool


class LangGraphResearchWorkflow:
    """在 ResearchWorkflow seam 后编排第一条真实网页研究链路。"""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        search_provider: SearchProvider,
        page_reader: WebPageReader,
        results_per_question: int,
    ) -> None:
        self._llm_client = llm_client
        self._search_provider = search_provider
        self._page_reader = page_reader
        self._results_per_question = results_per_question
        builder = StateGraph(_ResearchState)
        builder.add_node("planning", self._planning)
        builder.add_node("searching", self._searching)
        builder.add_node("reading", self._reading)
        builder.add_node("extracting", self._extracting)
        builder.add_node("writing", self._writing)
        builder.add_node("checking", self._checking)
        builder.add_edge(START, "planning")
        builder.add_edge("planning", "searching")
        builder.add_edge("searching", "reading")
        builder.add_edge("reading", "extracting")
        builder.add_edge("extracting", "writing")
        builder.add_edge("writing", "checking")
        builder.add_edge("checking", END)
        self._graph = builder.compile()

    async def execute(self, run_id: UUID, goal: str) -> AsyncIterator[ResearchWorkflowUpdate]:
        yield ResearchWorkflowUpdate(
            status=ResearchRunStatus.RUNNING,
            progress=2,
            started_at=datetime.now(UTC),
            events=(
                ResearchEventDraft(
                    type="run.started",
                    message="LangGraph 网页研究工作流开始执行",
                    progress=2,
                ),
            ),
        )
        try:
            async for chunk in self._graph.astream(
                {"run_id": str(run_id), "goal": goal, "warnings": ()},
                stream_mode="updates",
            ):
                update = self._to_workflow_update(chunk)
                if update is not None:
                    yield update
        except (LLMClientError, WebResearchError) as error:
            yield self._failure(error.code, error.public_message)

    async def _planning(self, state: _ResearchState) -> dict[str, Any]:
        result = await self._llm_client.create_research_plan(state["goal"])
        run_id = UUID(state["run_id"])
        plan = ResearchPlan(
            run_id=run_id,
            summary=result.plan.summary,
            questions=tuple(
                ResearchQuestion(
                    id=f"q{index}",
                    question=question.question,
                    rationale=question.rationale,
                    search_query=question.search_query,
                )
                for index, question in enumerate(result.plan.questions, start=1)
            ),
            deliverables=result.plan.deliverables,
            provider=result.provider,
            model=result.model,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            total_tokens=result.usage.total_tokens,
            duration_ms=result.duration_ms,
            created_at=datetime.now(UTC),
        )
        return {"plan": plan}

    async def _searching(self, state: _ResearchState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        now = datetime.now(UTC)
        tasks: list[ResearchTask] = []
        results: list[tuple[str, SearchResult]] = []
        warnings = list(state.get("warnings", ()))
        for index, question in enumerate(state["plan"].questions, start=1):
            task_id = f"t{index}"
            try:
                found = await self._search_provider.search(
                    question.search_query,
                    limit=self._results_per_question,
                )
            except WebResearchError as error:
                warnings.append(f"{question.id}: {error.public_message}")
                found = ()
            tasks.append(
                ResearchTask(
                    id=task_id,
                    run_id=run_id,
                    question_id=question.id,
                    query=question.search_query,
                    status=(ResearchTaskStatus.COMPLETED if found else ResearchTaskStatus.FAILED),
                    created_at=now,
                )
            )
            results.extend((task_id, item) for item in found)
        if not results:
            raise WebResearchError("SEARCH_NO_RESULTS", "没有找到可用于本次研究的网页来源")
        return {
            "tasks": tuple(tasks),
            "search_results": tuple(results),
            "warnings": tuple(warnings),
        }

    async def _reading(self, state: _ResearchState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        task_by_id = {task.id: task for task in state["tasks"]}
        documents: list[ResearchDocumentInput] = []
        sources: list[Source] = []
        warnings = list(state.get("warnings", ()))
        seen_urls: set[str] = set()
        for task_id, result in state["search_results"]:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            try:
                document = await self._page_reader.read(result)
            except WebResearchError as error:
                warnings.append(f"{result.url}: {error.public_message}")
                continue
            source_id = f"s{len(sources) + 1}"
            sources.append(
                Source(
                    id=source_id,
                    run_id=run_id,
                    task_id=task_id,
                    title=document.title,
                    url=document.url,
                    snippet=result.snippet[:500],
                    retrieved_at=datetime.now(UTC),
                )
            )
            documents.append(
                ResearchDocumentInput(
                    source_id=source_id,
                    title=document.title,
                    url=document.url,
                    content=document.content,
                )
            )
        if not documents:
            raise WebResearchError("WEB_CONTENT_UNAVAILABLE", "搜索结果中没有可读取的网页正文")
        valid_task_ids = {source.task_id for source in sources}
        tasks = tuple(
            task
            if task.id in valid_task_ids
            else ResearchTask(
                id=task.id,
                run_id=task.run_id,
                question_id=task.question_id,
                query=task.query,
                status=ResearchTaskStatus.FAILED,
                created_at=task.created_at,
            )
            for task in task_by_id.values()
        )
        return {
            "tasks": tasks,
            "documents": tuple(documents),
            "sources": tuple(sources),
            "warnings": tuple(warnings),
        }

    async def _extracting(self, state: _ResearchState) -> dict[str, Any]:
        plan = state["plan"]
        result = await self._llm_client.extract_evidence(
            state["goal"],
            tuple(
                ResearchQuestionDraft(
                    question=question.question,
                    rationale=question.rationale,
                    search_query=question.search_query,
                )
                for question in plan.questions
            ),
            state["documents"],
        )
        source_by_id = {source.id: source for source in state["sources"]}
        evidence = tuple(
            Evidence(
                id=f"e{index}",
                run_id=plan.run_id,
                task_id=source_by_id[item.source_id].task_id,
                question_id=item.question_id,
                source_id=item.source_id,
                excerpt=item.excerpt,
                summary=item.summary,
                created_at=datetime.now(UTC),
            )
            for index, item in enumerate(result.evidence, start=1)
            if item.source_id in source_by_id
        )
        if not evidence:
            raise LLMClientError("EVIDENCE_NOT_FOUND", "没有从网页资料中提取到有效证据")
        return {"evidence": evidence, "evidence_drafts": result.evidence}

    async def _writing(self, state: _ResearchState) -> dict[str, Any]:
        plan = state["plan"]
        result = await self._llm_client.write_research_report(
            state["goal"],
            ResearchPlanDraft(
                summary=plan.summary,
                questions=tuple(
                    ResearchQuestionDraft(
                        question=question.question,
                        rationale=question.rationale,
                        search_query=question.search_query,
                    )
                    for question in plan.questions
                ),
                deliverables=plan.deliverables,
            ),
            state["evidence_drafts"],
            state["documents"],
        )
        return {"report_markdown": result.report_markdown}

    async def _checking(self, state: _ResearchState) -> dict[str, Any]:
        source_ids = {source.id for source in state["sources"]}
        linked_source_ids = {item.source_id for item in state["evidence"]}
        has_source_link = any(source.url in state["report_markdown"] for source in state["sources"])
        passed = bool(state["evidence"]) and linked_source_ids <= source_ids and has_source_link
        if not passed:
            raise LLMClientError(
                "REPORT_EVIDENCE_CHECK_FAILED",
                "报告未通过来源与证据检查",
            )
        return {
            "check_passed": True,
            "report_markdown": state["report_markdown"],
        }

    @staticmethod
    def _to_workflow_update(chunk: dict[str, Any]) -> ResearchWorkflowUpdate | None:
        if not chunk:
            return None
        node_name, state_update = next(iter(chunk.items()))
        if node_name == "planning":
            plan = state_update["plan"]
            return ResearchWorkflowUpdate(
                stage=ResearchStage.PLANNING,
                progress=20,
                plan=plan,
                events=(
                    ResearchEventDraft(
                        type="research.plan.completed",
                        stage=ResearchStage.PLANNING,
                        message="结构化研究计划已经生成",
                        progress=20,
                        payload={"provider": plan.provider, "model": plan.model},
                    ),
                ),
            )
        if node_name == "searching":
            tasks = state_update["tasks"]
            return ResearchWorkflowUpdate(
                stage=ResearchStage.RETRIEVING,
                progress=38,
                tasks=tasks,
                events=(
                    ResearchEventDraft(
                        type="research.tasks.completed",
                        stage=ResearchStage.RETRIEVING,
                        message=f"已完成 {len(tasks)} 个网页检索任务",
                        progress=38,
                        payload={"task_count": len(tasks)},
                    ),
                ),
            )
        if node_name == "reading":
            return ResearchWorkflowUpdate(
                stage=ResearchStage.RETRIEVING,
                progress=56,
                tasks=state_update["tasks"],
                sources=state_update["sources"],
                events=(
                    ResearchEventDraft(
                        type="research.sources.completed",
                        stage=ResearchStage.RETRIEVING,
                        message=f"已读取并保存 {len(state_update['sources'])} 个网页来源",
                        progress=56,
                        payload={
                            "source_count": len(state_update["sources"]),
                            "warning_count": len(state_update.get("warnings", ())),
                        },
                    ),
                ),
            )
        if node_name == "extracting":
            return ResearchWorkflowUpdate(
                stage=ResearchStage.ANALYZING,
                progress=74,
                evidence=state_update["evidence"],
                events=(
                    ResearchEventDraft(
                        type="research.evidence.completed",
                        stage=ResearchStage.ANALYZING,
                        message=f"已提取并保存 {len(state_update['evidence'])} 条研究证据",
                        progress=74,
                        payload={"evidence_count": len(state_update["evidence"])},
                    ),
                ),
            )
        if node_name == "writing":
            return ResearchWorkflowUpdate(
                stage=ResearchStage.WRITING,
                progress=90,
                events=(
                    ResearchEventDraft(
                        type="report.draft.completed",
                        stage=ResearchStage.WRITING,
                        message="基于网页证据的报告草稿已经生成",
                        progress=90,
                    ),
                ),
            )
        if node_name == "checking":
            return ResearchWorkflowUpdate(
                outcome=ResearchRunOutcome(
                    status=ResearchRunStatus.COMPLETED,
                    progress=100,
                    stage=ResearchStage.FINALIZING,
                    report_markdown=state_update.get("report_markdown"),
                    error_code=None,
                    error_message=None,
                    events=(
                        ResearchEventDraft(
                            type="report.completed",
                            stage=ResearchStage.FINALIZING,
                            message="报告已通过来源与证据检查",
                            progress=100,
                        ),
                        ResearchEventDraft(
                            type="run.completed",
                            stage=ResearchStage.FINALIZING,
                            message="真实网页研究任务已完成",
                            progress=100,
                        ),
                    ),
                )
            )
        return None

    @staticmethod
    def _failure(code: str, message: str) -> ResearchWorkflowUpdate:
        return ResearchWorkflowUpdate(
            outcome=ResearchRunOutcome(
                status=ResearchRunStatus.FAILED,
                progress=None,
                stage=None,
                report_markdown=None,
                error_code=code,
                error_message=message,
                events=(
                    ResearchEventDraft(
                        type="run.failed",
                        message=message,
                        payload={"code": code},
                    ),
                ),
            )
        )
