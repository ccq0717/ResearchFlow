import { describe, expect, it } from "vitest";
import type { ResearchEventData } from "./api";
import { hasTerminalResearchEvent, mergeResearchEvents } from "./event-stream";

function event(sequence: number, type = "stage.started"): ResearchEventData {
  return {
    sequence,
    run_id: "run-1",
    type,
    stage: "planning",
    message: `事件 ${sequence}`,
    progress: sequence * 10,
    created_at: "2026-08-24T08:00:00Z",
    payload: {},
  };
}

describe("研究事件流", () => {
  it("按序号合并事件并忽略重复项", () => {
    expect(mergeResearchEvents([event(1), event(3)], [event(2), event(3)])).toEqual([
      event(1),
      event(2),
      event(3),
    ]);
  });

  it("识别成功、失败和取消终态事件", () => {
    expect(hasTerminalResearchEvent([event(1), event(2, "run.completed")])).toBe(true);
    expect(hasTerminalResearchEvent([event(1), event(2, "run.failed")])).toBe(true);
    expect(hasTerminalResearchEvent([event(1), event(2, "run.cancelled")])).toBe(true);
    expect(hasTerminalResearchEvent([event(1), event(2)])).toBe(false);
  });
});