from researchflow.integrations.llm.base import (
    EvidenceDraft,
    LLMEvidenceResult,
    LLMPlanResult,
    LLMReportResult,
    LLMUsage,
    ResearchDocumentInput,
    ResearchPlanDraft,
    ResearchQuestionDraft,
)


class FakeLLMClient:
    """不访问网络的确定性模型适配器，供自动化测试使用。"""

    async def create_research_plan(self, goal: str) -> LLMPlanResult:
        return LLMPlanResult(
            plan=ResearchPlanDraft(
                summary=f"围绕“{goal}”梳理评测对象、证据来源和可复现实验。",
                questions=(
                    ResearchQuestionDraft(
                        question="工业界现有工具采用哪些核心评测指标？",
                        rationale="确定产品能力、效率与体验的基线。",
                        search_query="AI code generation evaluation metrics",
                    ),
                    ResearchQuestionDraft(
                        question="学术界有哪些代表性数据集与基准？",
                        rationale="寻找可复现且有同行评议依据的方法。",
                        search_query="code generation benchmark dataset",
                    ),
                    ResearchQuestionDraft(
                        question="如何组合自动指标与人工评审？",
                        rationale="兼顾规模化测试和真实使用质量。",
                        search_query="automated code evaluation human review",
                    ),
                ),
                deliverables=("相关工作综述", "指标体系", "可执行评测流程"),
            ),
            provider="fake",
            model="fake-research-planner",
            usage=LLMUsage(input_tokens=32, output_tokens=96, total_tokens=128),
            duration_ms=1,
        )

    async def extract_evidence(
        self,
        goal: str,
        questions: tuple[ResearchQuestionDraft, ...],
        documents: tuple[ResearchDocumentInput, ...],
    ) -> LLMEvidenceResult:
        del goal
        evidence = tuple(
            EvidenceDraft(
                source_id=document.source_id,
                question_id=f"q{index % len(questions) + 1}",
                excerpt=document.content[:240],
                summary="该来源支持采用可复现任务、质量指标、安全检查和效率指标进行综合评测。",
            )
            for index, document in enumerate(documents)
        )
        return LLMEvidenceResult(
            evidence=evidence,
            usage=LLMUsage(input_tokens=120, output_tokens=180, total_tokens=300),
            duration_ms=1,
        )

    async def write_research_report(
        self,
        goal: str,
        plan: ResearchPlanDraft,
        evidence: tuple[EvidenceDraft, ...],
        documents: tuple[ResearchDocumentInput, ...],
    ) -> LLMReportResult:
        sources = "\n".join(f"- [{document.title}]({document.url})" for document in documents)
        findings = "\n".join(
            f"- {item.summary}（证据 {index}）" for index, item in enumerate(evidence, start=1)
        )
        report = f"""# AI 研究报告（M2 网页研究）

## 研究目标

{goal}

## 研究计划

{plan.summary}

## 主要发现

{findings}

## 建议

采用分层指标、固定任务集、自动化测试和人工审查组合的评测流程，并单独记录安全与开发效率结果。

## 来源

{sources}
"""
        return LLMReportResult(
            report_markdown=report,
            usage=LLMUsage(input_tokens=240, output_tokens=320, total_tokens=560),
            duration_ms=1,
        )
