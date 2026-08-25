import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ResearchMaterials } from "@/lib/api";
import { ResearchMaterialsPanel } from "./research-materials-panel";

const materials: ResearchMaterials = {
  run_id: "run-1",
  tasks: [],
  sources: [
    {
      id: "s1",
      run_id: "run-1",
      task_id: "t1",
      title: "Evaluation paper",
      url: "https://arxiv.org/abs/2401.00001",
      snippet: "A reproducible evaluation method.",
      retrieved_at: "2026-08-26T00:00:00Z",
      source_type: "academic",
      author: "Research Team",
      published_at: "2026-07-01T00:00:00Z",
      publisher: "arxiv.org",
    },
  ],
  evidence: [
    {
      id: "e1",
      run_id: "run-1",
      task_id: "t1",
      question_id: "q1",
      source_id: "s1",
      excerpt: "Use reproducible tasks.",
      summary: "The paper supports reproducible evaluation.",
      created_at: "2026-08-26T00:00:00Z",
    },
  ],
  claims: [
    {
      id: "c1",
      run_id: "run-1",
      question_id: "q1",
      text: "Evaluation should use reproducible tasks.",
      evidence_ids: ["e1"],
      created_at: "2026-08-26T00:00:00Z",
    },
  ],
  citation_audit: {
    claim_count: 1,
    supported_claim_count: 1,
    coverage_percent: 100,
    unsupported_claim_ids: [],
    source_type_counts: {
      academic: 1,
      official: 0,
      industry: 0,
      community: 0,
      other: 0,
    },
  },
};

describe("ResearchMaterialsPanel", () => {
  it("renders source types, citation coverage and claim evidence links", () => {
    const html = renderToStaticMarkup(<ResearchMaterialsPanel materials={materials} />);

    expect(html).toContain("学术");
    expect(html).toContain("引用覆盖 100%");
    expect(html).toContain("Evaluation should use reproducible tasks.");
    expect(html).toContain('href="https://arxiv.org/abs/2401.00001"');
  });
});
