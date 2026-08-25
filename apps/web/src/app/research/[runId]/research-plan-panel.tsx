import type { ResearchPlan } from "@/lib/api";
import { formatDuration } from "@/lib/format";

interface ResearchPlanPanelProps {
  plan: ResearchPlan | null;
}

export function ResearchPlanPanel({ plan }: ResearchPlanPanelProps) {
  return (
    <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">结构化研究计划</h2>
        {plan && (
          <span className="rounded-full bg-[#edf3ef] px-2.5 py-1 text-xs text-[#2f6f5e]">
            {plan.model}
          </span>
        )}
      </div>
      {plan ? (
        <div className="mt-4 space-y-5 text-sm">
          <p className="leading-6 text-[#4f5953]">{plan.summary}</p>
          <div>
            <h3 className="font-semibold text-[#7b4f2f]">核心问题</h3>
            <ol className="mt-2 space-y-3">
              {plan.questions.map((question, index) => (
                <li
                  className="rounded-2xl bg-[#f6f3ec] p-3"
                  key={question.id}
                >
                  <p className="font-medium">
                    {index + 1}. {question.question}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-[#737a75]">
                    {question.rationale}
                  </p>
                  <p className="mt-2 font-mono text-[11px] text-[#8a6a50]">
                    检索词：{question.search_query}
                  </p>
                </li>
              ))}
            </ol>
          </div>
          <div>
            <h3 className="font-semibold text-[#7b4f2f]">预期交付物</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-[#4f5953]">
              {plan.deliverables.map((deliverable) => (
                <li key={deliverable}>{deliverable}</li>
              ))}
            </ul>
          </div>
          <p
            className="border-t border-[#e5e0d6] pt-3 text-xs text-[#777c78]"
            title={`精确模型调用耗时：${plan.duration_ms} ms`}
          >
            {plan.provider} · {formatDuration(plan.duration_ms)} ·{" "}
            {plan.total_tokens ?? "—"} tokens
          </p>
        </div>
      ) : (
        <p className="mt-4 text-sm leading-6 text-[#737a75]">
          等待真实 LLM 规划结果。默认模拟模式不会生成这部分数据。
        </p>
      )}
    </section>
  );
}
