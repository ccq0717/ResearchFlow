import { afterEach, describe, expect, it, vi } from "vitest";
import { cancelResearchRun } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cancelResearchRun", () => {
  it("通过公开取消端点返回最新任务", async () => {
    const response = {
      id: "run-1",
      status: "cancelled",
      goal: "研究目标",
      title: "研究目标",
      current_stage: "planning",
      progress: 2,
      report_markdown: null,
      error_code: null,
      error_message: null,
      created_at: "2026-08-27T00:00:00Z",
      updated_at: "2026-08-27T00:01:00Z",
      started_at: "2026-08-27T00:00:01Z",
      completed_at: "2026-08-27T00:01:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(cancelResearchRun("run-1")).resolves.toEqual(response);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/research-runs/run-1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
