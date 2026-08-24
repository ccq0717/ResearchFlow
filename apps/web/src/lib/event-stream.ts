import type { ResearchEventData } from "./api";

const terminalEventTypes = new Set([
  "run.completed",
  "run.failed",
  "run.cancelled",
]);

export function mergeResearchEvents(
  current: ResearchEventData[],
  incoming: ResearchEventData[],
): ResearchEventData[] {
  const bySequence = new Map(
    current.map((event) => [event.sequence, event] as const),
  );
  for (const event of incoming) {
    bySequence.set(event.sequence, event);
  }
  return [...bySequence.values()].sort(
    (left, right) => left.sequence - right.sequence,
  );
}

export function hasTerminalResearchEvent(
  events: ResearchEventData[],
): boolean {
  return events.some((event) => terminalEventTypes.has(event.type));
}