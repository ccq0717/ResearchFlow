import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ResearchMetricsPanel } from "./research-metrics-panel";

describe("ResearchMetricsPanel", () => {
  it("展示运行成本与检索质量的核心指标", () => {
    const html = renderToStaticMarkup(
      <ResearchMetricsPanel
        metrics={{
          duration_ms: 12_000,
          llm_duration_ms: 8_000,
          input_tokens: 400,
          output_tokens: 600,
          total_tokens: 1_000,
          estimated_llm_cost_usd: null,
          task_count: 3,
          failed_task_count: 0,
          source_count: 6,
          web_source_count: 4,
          local_source_count: 2,
          evidence_count: 6,
          claim_count: 3,
          citation_coverage_percent: 100,
        }}
      />,
    );

    expect(html).toContain("12秒");
    expect(html).toContain("1,000");
    expect(html).toContain("网页 4 / 本地 2");
    expect(html).toContain("100%");
    expect(html).toContain("未配置单价");
  });
});
