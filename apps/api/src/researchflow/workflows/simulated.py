import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from researchflow.domain.research import (
    ResearchEventDraft,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
)
from researchflow.workflows.base import ResearchWorkflowUpdate, workflow_started_update


class SimulatedResearchWorkflow:
    def __init__(self, step_delay: float) -> None:
        self._step_delay = step_delay

    async def execute(self, run_id: UUID, goal: str) -> AsyncIterator[ResearchWorkflowUpdate]:
        yield workflow_started_update("研究工作流开始执行")

        stages = [
            (ResearchStage.PLANNING, 15, "正在拆解研究目标并生成研究计划"),
            (ResearchStage.RETRIEVING, 38, "正在检索学术资料和工业界实践"),
            (ResearchStage.ANALYZING, 62, "正在提取证据并比较评测方法"),
            (ResearchStage.WRITING, 84, "正在撰写结构化评测方案"),
            (ResearchStage.FINALIZING, 96, "正在检查报告结构和引用"),
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
                report_markdown=self._build_report(goal),
                error_code=None,
                error_message=None,
                events=(
                    ResearchEventDraft(
                        type="report.completed",
                        stage=ResearchStage.FINALIZING,
                        message="模拟研究报告已经生成",
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
    def _build_report(goal: str) -> str:
        return f"""# AI 研究方案（模拟结果）

## 研究目标

{goal}

## 初步研究框架

1. 明确目标用户、任务类型和候选工具；
2. 调研学术基准与工业界评测实践；
3. 建立功能、质量、安全和效率指标；
4. 设计可复现的数据集、实验流程和评分方法；
5. 保存证据与来源，验证结论和引用。

## 模式说明

当前内容由模拟工作流生成，不会调用外部 LLM 或网页搜索服务。若要执行真实网页研究，
请将工作流模式切换为 `langgraph`。
"""
