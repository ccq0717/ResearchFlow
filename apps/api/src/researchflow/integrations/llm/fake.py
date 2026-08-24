from researchflow.integrations.llm.base import (
    LLMPlanResult,
    LLMUsage,
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
                    ),
                    ResearchQuestionDraft(
                        question="学术界有哪些代表性数据集与基准？",
                        rationale="寻找可复现且有同行评议依据的方法。",
                    ),
                    ResearchQuestionDraft(
                        question="如何组合自动指标与人工评审？",
                        rationale="兼顾规模化测试和真实使用质量。",
                    ),
                ),
                deliverables=("相关工作综述", "指标体系", "可执行评测流程"),
            ),
            provider="fake",
            model="fake-research-planner",
            usage=LLMUsage(input_tokens=32, output_tokens=96, total_tokens=128),
            duration_ms=1,
        )
