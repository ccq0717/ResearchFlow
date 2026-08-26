import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from researchflow.domain.research import (
    ResearchEventDraft,
    ResearchPlan,
    ResearchQuestion,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
)
from researchflow.integrations.llm.base import LLMClient, LLMClientError
from researchflow.workflows.base import (
    ResearchWorkflowUpdate,
    workflow_failure_update,
    workflow_started_update,
)


class LLMResearchWorkflow:
    """使用真实模型生成计划，后续阶段暂用轻量模拟实现。"""

    def __init__(self, llm_client: LLMClient, step_delay: float) -> None:
        self._llm_client = llm_client
        self._step_delay = step_delay

    async def execute(
        self,
        run_id: UUID,
        goal: str,
        document_ids: tuple[UUID, ...] = (),
    ) -> AsyncIterator[ResearchWorkflowUpdate]:
        del document_ids
        yield workflow_started_update("研究工作流开始执行")
        yield ResearchWorkflowUpdate(
            stage=ResearchStage.PLANNING,
            progress=10,
            events=(
                ResearchEventDraft(
                    type="stage.started",
                    stage=ResearchStage.PLANNING,
                    message="正在调用模型拆解研究目标",
                    progress=10,
                ),
            ),
        )

        try:
            result = await self._llm_client.create_research_plan(goal)
        except LLMClientError as error:
            yield workflow_failure_update(error.code, error.public_message)
            return

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
        yield ResearchWorkflowUpdate(
            progress=25,
            plan=plan,
            events=(
                ResearchEventDraft(
                    type="research.plan.completed",
                    stage=ResearchStage.PLANNING,
                    message="结构化研究计划已经生成",
                    progress=25,
                    payload={
                        "provider": plan.provider,
                        "model": plan.model,
                        "duration_ms": plan.duration_ms,
                        "total_tokens": plan.total_tokens,
                    },
                ),
                ResearchEventDraft(
                    type="stage.completed",
                    stage=ResearchStage.PLANNING,
                    message="研究目标拆解与计划生成：已完成",
                    progress=25,
                ),
            ),
        )

        stages = [
            (ResearchStage.RETRIEVING, 42, "正在模拟检索学术资料和工业界实践"),
            (ResearchStage.ANALYZING, 64, "正在模拟提取证据并比较评测方法"),
            (ResearchStage.WRITING, 84, "正在根据真实研究计划整理演示报告"),
            (ResearchStage.FINALIZING, 96, "正在检查报告结构"),
        ]
        for stage, progress, message in stages:
            yield ResearchWorkflowUpdate(
                stage=stage,
                progress=progress,
                events=(
                    ResearchEventDraft(
                        type="stage.started",
                        stage=stage,
                        message=message,
                        progress=progress,
                    ),
                ),
            )
            await asyncio.sleep(self._step_delay)
            yield ResearchWorkflowUpdate(
                events=(
                    ResearchEventDraft(
                        type="stage.completed",
                        stage=stage,
                        message=f"{message}：已完成",
                        progress=progress,
                    ),
                ),
            )

        yield ResearchWorkflowUpdate(
            outcome=ResearchRunOutcome(
                status=ResearchRunStatus.COMPLETED,
                progress=100,
                stage=ResearchStage.FINALIZING,
                report_markdown=self._build_report(goal, plan),
                error_code=None,
                error_message=None,
                events=(
                    ResearchEventDraft(
                        type="report.completed",
                        stage=ResearchStage.FINALIZING,
                        message="基于真实研究计划的演示报告已经生成",
                        progress=100,
                    ),
                    ResearchEventDraft(
                        type="run.completed",
                        stage=ResearchStage.FINALIZING,
                        message="研究任务已完成",
                        progress=100,
                    ),
                ),
            )
        )

    @staticmethod
    def _build_report(goal: str, plan: ResearchPlan) -> str:
        questions = "\n".join(
            f"{index}. **{question.question}**\n   - 原因：{question.rationale}"
            for index, question in enumerate(plan.questions, start=1)
        )
        deliverables = "\n".join(f"- {deliverable}" for deliverable in plan.deliverables)
        return f"""# AI 研究方案（规划模式演示结果）

## 研究目标

{goal}

## 研究计划摘要

{plan.summary}

## 核心研究问题

{questions}

## 预期交付物

{deliverables}

## 当前实现边界

本模式只使用真实模型生成研究计划，检索、证据提取和报告仍使用轻量占位内容。
若要执行真实网页研究，请将工作流模式切换为 `langgraph`。
"""
