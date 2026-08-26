from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from researchflow.domain.knowledge import KnowledgeSearchHit
from researchflow.domain.research import (
    Claim,
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
    SourceOrigin,
    SourceType,
)
from researchflow.domain.source_quality import (
    classify_source,
    infer_publisher,
    parse_published_at,
)
from researchflow.ingestion.retrieval import KnowledgeRetriever
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
from researchflow.workflows.base import (
    ResearchWorkflowUpdate,
    workflow_failure_update,
    workflow_started_update,
)


class _ResearchState(TypedDict, total=False):
    run_id: str
    goal: str
    plan: ResearchPlan
    tasks: tuple[ResearchTask, ...]
    search_results: tuple[tuple[str, SearchResult], ...]
    documents: tuple[ResearchDocumentInput, ...]
    sources: tuple[Source, ...]
    evidence: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    evidence_drafts: tuple[EvidenceDraft, ...]
    report_markdown: str
    warnings: tuple[str, ...]
    document_ids: tuple[UUID, ...]
    local_hits: tuple[tuple[str, KnowledgeSearchHit], ...]
    check_passed: bool


class LangGraphResearchWorkflow:
    """在 ResearchWorkflow seam 后编排网页与本地资料联合研究链路。"""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        search_provider: SearchProvider,
        page_reader: WebPageReader,
        results_per_question: int,
        knowledge_retriever: KnowledgeRetriever,
        knowledge_results_per_question: int,
    ) -> None:
        self._llm_client = llm_client
        self._search_provider = search_provider
        self._page_reader = page_reader
        self._results_per_question = results_per_question
        self._knowledge_retriever = knowledge_retriever
        self._knowledge_results_per_question = knowledge_results_per_question
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

    async def execute(
        self,
        run_id: UUID,
        goal: str,
        document_ids: tuple[UUID, ...] = (),
    ) -> AsyncIterator[ResearchWorkflowUpdate]:
        yield workflow_started_update("LangGraph 联合研究工作流开始执行")
        try:
            async for chunk in self._graph.astream(
                {
                    "run_id": str(run_id),
                    "goal": goal,
                    "document_ids": document_ids,
                    "warnings": (),
                },
                stream_mode="updates",
            ):
                update = self._to_workflow_update(chunk)
                if update is not None:
                    yield update
        except (LLMClientError, WebResearchError) as error:
            yield workflow_failure_update(error.code, error.public_message)

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
        local_hits: list[tuple[str, KnowledgeSearchHit]] = []
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
            local_found = await self._knowledge_retriever.search(
                f"{question.question} {question.search_query}",
                state.get("document_ids", ()),
                limit=self._knowledge_results_per_question,
            )
            tasks.append(
                ResearchTask(
                    id=task_id,
                    run_id=run_id,
                    question_id=question.id,
                    query=question.search_query,
                    status=(
                        ResearchTaskStatus.COMPLETED
                        if found or local_found
                        else ResearchTaskStatus.FAILED
                    ),
                    created_at=now,
                )
            )
            results.extend((task_id, item) for item in found)
            local_hits.extend((task_id, item) for item in local_found)
        if not results and not local_hits:
            raise WebResearchError("SEARCH_NO_RESULTS", "没有找到可用于本次研究的网页或本地资料")
        return {
            "tasks": tuple(tasks),
            "search_results": tuple(results),
            "local_hits": tuple(local_hits),
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
                    source_type=classify_source(document.url),
                    author=result.author,
                    published_at=parse_published_at(result.published_at),
                    publisher=infer_publisher(document.url),
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
        seen_chunks: set[str] = set()
        for task_id, hit in state.get("local_hits", ()):
            if hit.chunk_id in seen_chunks:
                continue
            seen_chunks.add(hit.chunk_id)
            source_id = f"s{len(sources) + 1}"
            sources.append(
                Source(
                    id=source_id,
                    run_id=run_id,
                    task_id=task_id,
                    title=hit.document_title,
                    url=None,
                    snippet=hit.content[:500],
                    retrieved_at=datetime.now(UTC),
                    source_type=SourceType.OTHER,
                    publisher="本地知识库",
                    origin=SourceOrigin.LOCAL,
                    knowledge_document_id=hit.document_id,
                    locator=hit.locator,
                )
            )
            documents.append(
                ResearchDocumentInput(
                    source_id=source_id,
                    title=hit.document_title,
                    url=None,
                    content=hit.content,
                    locator=hit.locator,
                )
            )
        if not documents:
            raise WebResearchError(
                "WEB_CONTENT_UNAVAILABLE", "搜索结果中没有可读取的网页或本地正文"
            )
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
        question_ids = {question.id for question in plan.questions}
        document_by_source_id = {document.source_id: document for document in state["documents"]}
        valid_drafts = tuple(
            item
            for item in result.evidence
            if item.source_id in source_by_id
            and item.question_id in question_ids
            and self._excerpt_occurs_in_document(
                item.excerpt,
                document_by_source_id[item.source_id].content,
            )
        )
        now = datetime.now(UTC)
        evidence = tuple(
            Evidence(
                id=f"e{index}",
                run_id=plan.run_id,
                task_id=source_by_id[item.source_id].task_id,
                question_id=item.question_id,
                source_id=item.source_id,
                excerpt=item.excerpt,
                summary=item.summary,
                created_at=now,
            )
            for index, item in enumerate(valid_drafts, start=1)
        )
        if not evidence:
            raise LLMClientError("EVIDENCE_NOT_FOUND", "没有从网页或本地资料中提取到有效证据")
        evidence_ids_by_claim: dict[tuple[str, str], list[str]] = {}
        for item, evidence_item in zip(valid_drafts, evidence, strict=True):
            claim_text = " ".join(item.claim.split())
            evidence_ids_by_claim.setdefault((item.question_id, claim_text), []).append(
                evidence_item.id
            )
        claims = tuple(
            Claim(
                id=f"c{index}",
                run_id=plan.run_id,
                question_id=question_id,
                text=claim_text,
                evidence_ids=tuple(evidence_ids),
                created_at=now,
            )
            for index, ((question_id, claim_text), evidence_ids) in enumerate(
                evidence_ids_by_claim.items(), start=1
            )
        )
        return {
            "evidence": evidence,
            "claims": claims,
            "evidence_drafts": valid_drafts,
        }

    @staticmethod
    def _excerpt_occurs_in_document(excerpt: str, content: str) -> bool:
        normalized_excerpt = " ".join(excerpt.casefold().split())
        normalized_content = " ".join(content.casefold().split())
        return bool(normalized_excerpt) and normalized_excerpt in normalized_content

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
        return {
            "report_markdown": self._append_traceability_section(
                result.report_markdown,
                state["claims"],
                state["evidence"],
                state["sources"],
            )
        }

    async def _checking(self, state: _ResearchState) -> dict[str, Any]:
        source_by_id = {source.id: source for source in state["sources"]}
        evidence_by_id = {item.id: item for item in state["evidence"]}
        unsupported_claims = tuple(
            claim.id
            for claim in state["claims"]
            if not claim.evidence_ids
            or not all(evidence_id in evidence_by_id for evidence_id in claim.evidence_ids)
        )
        has_missing_evidence_source = any(
            evidence_by_id[evidence_id].source_id not in source_by_id
            for claim in state["claims"]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        )
        cited_source_urls = {
            source_by_id[evidence_by_id[evidence_id].source_id].url
            for claim in state["claims"]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].source_id in source_by_id
            and source_by_id[evidence_by_id[evidence_id].source_id].origin is SourceOrigin.WEB
            and source_by_id[evidence_by_id[evidence_id].source_id].url
        }
        cited_local_sources = {
            source_by_id[evidence_by_id[evidence_id].source_id]
            for claim in state["claims"]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].source_id in source_by_id
            and source_by_id[evidence_by_id[evidence_id].source_id].origin is SourceOrigin.LOCAL
        }
        has_claim_sections = all(
            f"### {claim.id.upper()}" in state["report_markdown"] for claim in state["claims"]
        )
        passed = (
            bool(state["claims"])
            and not unsupported_claims
            and not has_missing_evidence_source
            and has_claim_sections
            and all(url in state["report_markdown"] for url in cited_source_urls)
            and all(
                source.locator
                and source.title in state["report_markdown"]
                and source.locator in state["report_markdown"]
                for source in cited_local_sources
            )
        )
        if not passed:
            raise LLMClientError(
                "REPORT_EVIDENCE_CHECK_FAILED",
                "报告未通过来源与证据检查",
            )
        return {
            "check_passed": True,
            "report_markdown": state["report_markdown"],
            "source_type_counts": {
                source_type: sum(source.source_type == source_type for source in state["sources"])
                for source_type in {source.source_type for source in state["sources"]}
            },
        }

    @staticmethod
    def _append_traceability_section(
        report_markdown: str,
        claims: tuple[Claim, ...],
        evidence: tuple[Evidence, ...],
        sources: tuple[Source, ...],
    ) -> str:
        evidence_by_id = {item.id: item for item in evidence}
        source_by_id = {source.id: source for source in sources}
        sections = [report_markdown.rstrip(), "", "## 可追溯主张与证据", ""]
        for claim in claims:
            sections.extend((f"### {claim.id.upper()}", "", claim.text, ""))
            for evidence_id in claim.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                if item is None:
                    continue
                source = source_by_id.get(item.source_id)
                if source is None:
                    continue
                citation = (
                    f"[{source.title}]({source.url})"
                    if source.url
                    else f"{source.title}，{source.locator or '本地文档'}"
                )
                sections.append(f"- {item.id.upper()}：{item.summary}（{citation}）")
            sections.append("")
        return "\n".join(sections).rstrip() + "\n"

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
                        message=f"已完成 {len(tasks)} 个网页与本地资料检索任务",
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
                        message=f"已读取并保存 {len(state_update['sources'])} 个网页或本地来源",
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
                claims=state_update["claims"],
                events=(
                    ResearchEventDraft(
                        type="research.evidence.completed",
                        stage=ResearchStage.ANALYZING,
                        message=(
                            f"已提取 {len(state_update['evidence'])} 条证据并建立 "
                            f"{len(state_update['claims'])} 条可追溯主张"
                        ),
                        progress=74,
                        payload={
                            "evidence_count": len(state_update["evidence"]),
                            "claim_count": len(state_update["claims"]),
                        },
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
                            message="报告已通过主张、证据与来源引用检查",
                            progress=100,
                            payload={
                                "citation_coverage_percent": 100,
                                "source_type_counts": state_update.get("source_type_counts", {}),
                            },
                        ),
                        ResearchEventDraft(
                            type="run.completed",
                            stage=ResearchStage.FINALIZING,
                            message="网页与本地资料联合研究任务已完成",
                            progress=100,
                        ),
                    ),
                )
            )
        return None
