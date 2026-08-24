import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from researchflow.domain.research import (
    ResearchEventDraft,
    ResearchRunOutcome,
    ResearchRunStatus,
    ResearchStage,
)
from researchflow.persistence.repository import SqliteResearchRepository

logger = logging.getLogger(__name__)


class SimulatedResearchWorkflow:
    def __init__(self, repository: SqliteResearchRepository, step_delay: float) -> None:
        self._repository = repository
        self._step_delay = step_delay

    async def execute(self, run_id: UUID, goal: str) -> None:
        try:
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

            stages = [
                (ResearchStage.PLANNING, 15, "正在拆解研究目标并生成研究计划"),
                (ResearchStage.RETRIEVING, 38, "正在检索学术资料和工业界实践"),
                (ResearchStage.ANALYZING, 62, "正在提取证据并比较评测方法"),
                (ResearchStage.WRITING, 84, "正在撰写结构化评测方案"),
                (ResearchStage.FINALIZING, 96, "正在检查报告结构和引用"),
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

            await self._repository.finalize(
                run_id,
                ResearchRunOutcome(
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
                ),
            )
        except Exception:
            logger.exception("模拟研究工作流执行失败，run_id=%s", run_id)
            await self._fail_run(run_id)

    async def _fail_run(self, run_id: UUID) -> None:
        message = "模拟研究工作流执行失败"
        await self._repository.finalize(
            run_id,
            ResearchRunOutcome(
                status=ResearchRunStatus.FAILED,
                progress=None,
                stage=None,
                report_markdown=None,
                error_code="SIMULATION_FAILED",
                error_message=message,
                events=(
                    ResearchEventDraft(
                        type="run.failed",
                        message=message,
                        payload={"code": "SIMULATION_FAILED"},
                    ),
                ),
            ),
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

## 下一阶段

当前内容由模拟工作流生成。后续里程碑将依次接入真实 LLM 规划、网页与论文检索、
证据提取、RAG 和引用验证。
"""
