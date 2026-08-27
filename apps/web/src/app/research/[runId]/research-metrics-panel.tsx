import type { ResearchRunMetrics } from "@/lib/api";
import { formatDuration } from "../../../lib/format";

export function ResearchMetricsPanel({ metrics }: { metrics: ResearchRunMetrics | null }) {
  if (!metrics) return null;
  const items = [
    ["总耗时", metrics.duration_ms === null ? "—" : formatDuration(metrics.duration_ms)],
    ["模型 Token", metrics.total_tokens?.toLocaleString() ?? "—"],
    ["来源", `${metrics.source_count}（网页 ${metrics.web_source_count} / 本地 ${metrics.local_source_count}）`],
    ["引用覆盖", `${metrics.citation_coverage_percent}%`],
    [
      "模型费用估算",
      metrics.estimated_llm_cost_usd === null
        ? "未配置单价"
        : `$${metrics.estimated_llm_cost_usd.toFixed(4)}`,
    ],
  ];
  return (
    <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6">
      <h2 className="font-semibold">运行度量</h2>
      <dl className="mt-4 space-y-3 text-sm">
        {items.map(([label, value]) => (
          <div className="flex justify-between gap-4" key={label}>
            <dt className="text-[#6d746f]">{label}</dt>
            <dd className="text-right font-medium">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
