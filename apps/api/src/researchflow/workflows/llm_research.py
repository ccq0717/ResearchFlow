import asyncio
from datetime import UTC, datetime
from uuid import UUID

from researchflow.domain.research import (
    ResearchPlan,
    ResearchQuestion,
    ResearchRunStatus,
    ResearchStage,
)
from researchflow.integrations.llm.base import LLMClient, LLMClientError
from researchflow.persistence.repository import SqliteResearchRepository


class LLMResearchWorkflow:
    """使用真实模型生成计划，后续阶段暂用轻量模拟实现。"""

    def __init__(
        self,
        repository: SqliteResearchRepository,
        llm_client: LLMClient,
        step_delay: float,
    ) -> None:
        self._repository = repository
        self._llm_client = llm_client
        self._step_delay = step_delay

    async def execute(self, run_id: UUID, goal: str) -> None:
        try:
            await self._start_run(run_id)
            plan = await self._create_plan(run_id, goal)
            await self._simulate_remaining_stages(run_id)
            await self._complete_run(run_id, goal, plan)
        except LLMClientError as error:
            await self._fail_run(run_id, error.code, error.public_message)
        except Exception:
            await self._fail_run(
                run_id,
                "WORKFLOW_FAILED",
                "研究工作流执行失败，请检查后端日志",
            )

    async def _start_run(self, run_id: UUID) -> None:
        await self._repository.update(
            run_id,
            status=ResearchRunStatus.RUNNING,
            progress=2,
            started_at=datetime.now(UTC),
        )
        await self._repository.append_event(
            run_id,
            event_type="run.started",
            message="研究工作流开始执行",
            progress=2,
        )

    async def _create_plan(self, run_id: UUID, goal: str) -> ResearchPlan:
        await self._repository.update(
            run_id,
            stage=ResearchStage.PLANNING,
            progress=10,
        )
        await self._repository.append_event(
            run_id,
            event_type="stage.started",
            stage=ResearchStage.PLANNING,
            message="正在调用模型拆解研究目标",
            progress=10,
        )

        result = await self._llm_client.create_research_plan(goal)
        plan = ResearchPlan(
            run_id=run_id,
            summary=result.plan.summary,
            questions=tuple(
                ResearchQuestion(
                    id=f"q{index}",
                    question=question.question,
                    rationale=question.rationale,
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
        await self._repository.save_plan(plan)
        await self._repository.update(run_id, progress=25)
        await self._repository.append_event(
            run_id,
            event_type="research.plan.completed",
            stage=ResearchStage.PLANNING,
            message="结构化研究计划已经生成",
            progress=25,
            payload={
                "provider": plan.provider,
                "model": plan.model,
                "duration_ms": plan.duration_ms,
                "total_tokens": plan.total_tokens,
            },
        )
        await self._repository.append_event(
            run_id,
            event_type="stage.completed",
            stage=ResearchStage.PLANNING,
            message="研究目标拆解与计划生成：已完成",
            progress=25,
        )
        return plan

    async def _simulate_remaining_stages(self, run_id: UUID) -> None:
        stages = [
            (ResearchStage.RETRIEVING, 42, "正在模拟检索学术资料和工业界实践"),
            (ResearchStage.ANALYZING, 64, "正在模拟提取证据并比较评测方法"),
            (ResearchStage.WRITING, 84, "正在根据真实研究计划整理演示报告"),
            (ResearchStage.FINALIZING, 96, "正在检查报告结构"),
        ]
        for stage, progress, message in stages:
            await self._repository.update(run_id, stage=stage, progress=progress)
            await self._repository.append_event(
                run_id,
                event_type="stage.started",
                stage=stage,
                message=message,
                progress=progress,
            )
            await asyncio.sleep(self._step_delay)
            await self._repository.append_event(
                run_id,
                event_type="stage.completed",
                stage=stage,
                message=f"{message}：已完成",
                progress=progress,
            )

    async def _complete_run(self, run_id: UUID, goal: str, plan: ResearchPlan) -> None:
        completed_at = datetime.now(UTC)
        await self._repository.update(
            run_id,
            status=ResearchRunStatus.COMPLETED,
            progress=100,
            report_markdown=self._build_report(goal, plan),
            completed_at=completed_at,
        )
        await self._repository.append_event(
            run_id,
            event_type="report.completed",
            stage=ResearchStage.FINALIZING,
            message="基于真实研究计划的演示报告已经生成",
            progress=100,
        )
        await self._repository.append_event(
            run_id,
            event_type="run.completed",
            stage=ResearchStage.FINALIZING,
            message="研究任务已完成",
            progress=100,
        )

    async def _fail_run(self, run_id: UUID, code: str, message: str) -> None:
        await self._repository.update(
            run_id,
            status=ResearchRunStatus.FAILED,
            error_code=code,
            error_message=message,
            completed_at=datetime.now(UTC),
        )
        await self._repository.append_event(
            run_id,
            event_type="run.failed",
            message=message,
            payload={"code": code},
        )

    @staticmethod
    def _build_report(goal: str, plan: ResearchPlan) -> str:
        questions = "\n".join(
            f"{index}. **{question.question}**\n   - 原因：{question.rationale}"
            for index, question in enumerate(plan.questions, start=1)
        )
        deliverables = "\n".join(f"- {deliverable}" for deliverable in plan.deliverables)
        return f"""# AI 研究方案（M1 演示结果）

## 研究目标

{goal}

## 研究计划摘要

{plan.summary}

## 核心研究问题

{questions}

## 预期交付物

{deliverables}

## 当前实现边界

本报告的研究计划由模型真实生成；检索、证据提取和引用验证仍为轻量模拟，
将在后续 M2 至 M4 里逐步接入。
"""
