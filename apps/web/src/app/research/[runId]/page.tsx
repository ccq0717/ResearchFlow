"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ResearchErrorPanel } from "./research-error-panel";
import { ResearchMaterialsPanel } from "./research-materials-panel";
import { ResearchMetricsPanel } from "./research-metrics-panel";
import { ResearchPlanPanel } from "./research-plan-panel";
import { ResearchReport } from "./research-report";
import {
  apiBaseUrl,
  cancelResearchRun,
  getResearchMaterials,
  getResearchPlan,
  getResearchRun,
  getResearchRunMetrics,
  listResearchEvents,
  retryResearchRun,
  type ResearchEventData,
  type ResearchMaterials,
  type ResearchPlan,
  type ResearchRun,
  type ResearchRunMetrics,
  type ResearchStage,
} from "@/lib/api";
import {
  hasTerminalResearchEvent,
  mergeResearchEvents,
} from "@/lib/event-stream";
import { formatEventTime } from "@/lib/format";

const stages: Array<{ id: ResearchStage; label: string }> = [
  { id: "planning", label: "规划问题" },
  { id: "retrieving", label: "检索资料" },
  { id: "analyzing", label: "分析证据" },
  { id: "writing", label: "撰写方案" },
  { id: "finalizing", label: "检查结果" },
];


export default function ResearchWorkspace() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const runId = params.runId;
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [plan, setPlan] = useState<ResearchPlan | null>(null);
  const [materials, setMaterials] = useState<ResearchMaterials | null>(null);
  const [metrics, setMetrics] = useState<ResearchRunMetrics | null>(null);
  const [events, setEvents] = useState<ResearchEventData[]>([]);
  const [connection, setConnection] = useState("正在连接");
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const terminal = useMemo(
    () =>
      run?.status === "completed" ||
      run?.status === "failed" ||
      run?.status === "cancelled",
    [run?.status],
  );

  useEffect(() => {
    let source: EventSource | null = null;
    let cancelled = false;

    async function start() {
      try {
        const [initial, initialPlan, initialMaterials] = await Promise.all([
          getResearchRun(runId),
          getResearchPlan(runId),
          getResearchMaterials(runId),
        ]);
        // 状态先于历史读取：若状态已经终结，原子提交的终结事件随后一定可见。
        const initialEvents = await listResearchEvents(runId);
        const historyIsTerminal = hasTerminalResearchEvent(initialEvents);
        const historyHasPlan = initialEvents.some(
          (event) => event.type === "research.plan.completed",
        );
        const historyHasMaterials = initialEvents.some((event) =>
          [
            "research.tasks.completed",
            "research.sources.completed",
            "research.evidence.completed",
          ].includes(event.type),
        );
        const [latestRun, latestPlan, latestMaterials] = await Promise.all([
          historyIsTerminal &&
          !["completed", "failed", "cancelled"].includes(initial.status)
            ? getResearchRun(runId)
            : initial,
          historyHasPlan && initialPlan === null
            ? getResearchPlan(runId)
            : initialPlan,
          historyHasMaterials
            ? getResearchMaterials(runId)
            : initialMaterials,
        ]);
        if (cancelled) return;
        setRun(latestRun);
        setPlan(latestPlan);
        setMaterials(latestMaterials);
        setEvents(initialEvents);
        if (
          historyIsTerminal ||
          ["completed", "failed", "cancelled"].includes(latestRun.status)
        ) {
          void getResearchRunMetrics(runId).then(setMetrics);
          setConnection("已结束");
          return;
        }

        const lastSequence = initialEvents.at(-1)?.sequence ?? 0;
        source = new EventSource(
          apiBaseUrl +
            "/api/research-runs/" +
            runId +
            "/events?after=" +
            lastSequence,
        );
        source.onopen = () => setConnection("实时连接");

        const handleEvent = (raw: Event) => {
          const message = raw as MessageEvent<string>;
          const data = JSON.parse(message.data) as ResearchEventData;
          if (data.type !== "stream.ready") {
            setEvents((current) => mergeResearchEvents(current, [data]));
          }
          if (data.type === "research.plan.completed") {
            void getResearchPlan(runId).then(setPlan);
          }
          if (
            data.type === "research.tasks.completed" ||
            data.type === "research.sources.completed" ||
            data.type === "research.evidence.completed"
          ) {
            void getResearchMaterials(runId).then(setMaterials);
          }
          setRun((current) =>
            current
              ? {
                  ...current,
                  current_stage: data.stage ?? current.current_stage,
                  progress: data.progress ?? current.progress,
                }
              : current,
          );

          if (
            data.type === "run.completed" ||
            data.type === "run.failed" ||
            data.type === "run.cancelled"
          ) {
            void Promise.all([
              getResearchRun(runId),
              getResearchPlan(runId),
              getResearchMaterials(runId),
              getResearchRunMetrics(runId),
            ]).then(([latestRun, latestPlan, latestMaterials, latestMetrics]) => {
              setRun(latestRun);
              setPlan(latestPlan);
              setMaterials(latestMaterials);
              setMetrics(latestMetrics);
            });
            source?.close();
            setConnection("已结束");
          }
        };

        source.addEventListener("research.event", handleEvent);
        source.addEventListener("stream.ready", handleEvent);
        source.onerror = () => setConnection("连接中断");
      } catch {
        setError("无法读取研究任务，请确认后端已经启动。");
        setConnection("连接失败");
      }
    }

    start();
    return () => {
      cancelled = true;
      source?.close();
    };
  }, [runId]);

  async function handleCancel() {
    setCancelling(true);
    setActionError(null);
    try {
      setRun(await cancelResearchRun(runId));
      setMetrics(await getResearchRunMetrics(runId));
      setConnection("已结束");
    } catch {
      setActionError("无法取消研究任务，请刷新后确认任务状态。");
    } finally {
      setCancelling(false);
    }
  }

  async function handleRetry() {
    setRetrying(true);
    setActionError(null);
    try {
      const nextRun = await retryResearchRun(runId);
      router.push("/research/" + nextRun.id);
    } catch {
      setActionError("无法重试研究任务；每个失败任务最多重试一次。");
      setRetrying(false);
    }
  }

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f4f1e9] p-6">
        <div className="max-w-lg rounded-3xl bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-semibold">无法打开研究任务</h1>
          <p className="mt-3 text-[#6d746f]">{error}</p>
          <Link className="mt-6 inline-block text-[#2f6f5e] underline" href="/">
            返回 Dashboard
          </Link>
        </div>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="min-h-screen bg-[#f4f1e9] p-8">
        正在加载研究任务…
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f4f1e9] text-[#17231d]">
      <header className="border-b border-[#d8d3c7] bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link className="font-semibold" href="/">
            ← ResearchFlow
          </Link>
          <div className="flex items-center gap-2 text-sm text-[#6d746f]">
            <span
              className={
                "h-2 w-2 rounded-full " +
                (terminal ? "bg-[#6d746f]" : "bg-emerald-500")
              }
            />
            {connection}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="rounded-3xl bg-[#173f35] p-7 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#b9d9c7]">
            Research workspace
          </p>
          <h1 className="mt-3 max-w-4xl text-2xl font-semibold leading-9 sm:text-3xl">
            {run.goal}
          </h1>
          <div className="mt-6 flex items-center gap-4">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/15">
              <div
                className="h-full rounded-full bg-[#e98950] transition-all duration-500"
                style={{ width: run.progress + "%" }}
              />
            </div>
            <span className="w-12 text-right text-sm font-semibold">
              {run.progress}%
            </span>
          </div>
          {(!terminal || (run.status === "failed" && run.attempt < 2)) && (
            <div className="mt-5 flex items-center gap-4">
              {!terminal && (
                <button
                  className="rounded-full border border-white/40 px-4 py-2 text-sm font-semibold transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={cancelling}
                  onClick={handleCancel}
                  type="button"
                >
                  {cancelling ? "正在取消…" : "取消研究"}
                </button>
              )}
              {run.status === "failed" && run.attempt < 2 && (
                <button
                  className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#173f35] disabled:opacity-60"
                  disabled={retrying}
                  onClick={handleRetry}
                  type="button"
                >
                  {retrying ? "正在重试…" : "重新运行一次"}
                </button>
              )}
              {actionError && (
                <p className="text-sm text-[#ffd4bd]">{actionError}</p>
              )}
            </div>
          )}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[0.72fr_1.28fr]">
          <aside className="space-y-6">
            <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6">
              <h2 className="font-semibold">研究阶段</h2>
              <div className="mt-5 space-y-4">
                {stages.map((stage, index) => {
                  const currentIndex = stages.findIndex(
                    (item) => item.id === run.current_stage,
                  );
                  const completed =
                    run.status === "completed" || index < currentIndex;
                  const active = stage.id === run.current_stage && !terminal;
                  return (
                    <div className="flex items-center gap-3" key={stage.id}>
                      <span
                        className={
                          "grid h-7 w-7 place-items-center rounded-full text-xs font-semibold " +
                          (completed
                            ? "bg-[#2f6f5e] text-white"
                            : active
                              ? "bg-[#f4c7a9] text-[#7b3d1c]"
                              : "bg-[#ece8df] text-[#7c817d]")
                        }
                      >
                        {completed ? "✓" : index + 1}
                      </span>
                      <span
                        className={
                          active ? "font-semibold" : "text-[#626a65]"
                        }
                      >
                        {stage.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            <ResearchPlanPanel plan={plan} />

            <ResearchMaterialsPanel materials={materials} />

            <ResearchMetricsPanel metrics={metrics} />

            <section className="rounded-3xl border border-[#d8d3c7] bg-[#ebe5d9] p-6">
              <h2 className="font-semibold">研究事件</h2>
              <div className="mt-4 max-h-72 space-y-3 overflow-auto">
                {events.length === 0 && (
                  <p className="text-sm text-[#6d746f]">等待研究事件…</p>
                )}
                {events.map((event) => (
                  <div
                    className="border-l-2 border-[#a7b8af] pl-3 text-sm"
                    key={event.sequence}
                  >
                    <p>{event.message}</p>
                    <p className="mt-1 text-xs text-[#777c78]">
                      {formatEventTime(event.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </aside>

          <section className="min-h-[34rem] rounded-3xl border border-[#d8d3c7] bg-white p-6 sm:p-8">
            <div className="flex items-center justify-between border-b border-[#e5e0d6] pb-5">
              <div>
                <p className="text-sm font-semibold text-[#7b4f2f]">REPORT</p>
                <h2 className="mt-1 text-2xl font-semibold">研究结果</h2>
              </div>
              <span className="rounded-full bg-[#edf3ef] px-3 py-1 text-sm text-[#2f6f5e]">
                {run.status} · 第 {run.attempt} 次运行
              </span>
            </div>
            {run.status === "failed" ? (
              <ResearchErrorPanel
                code={run.error_code}
                message={run.error_message}
              />
            ) : run.status === "cancelled" ? (
              <div className="grid min-h-96 place-items-center text-center text-[#737a75]">
                <p>研究任务已取消，已保存的计划、来源和证据仍可查看。</p>
              </div>
            ) : run.report_markdown ? (
              <ResearchReport markdown={run.report_markdown} />
            ) : (
              <div className="grid min-h-96 place-items-center text-center text-[#737a75]">
                <div>
                  <div className="mx-auto h-12 w-12 animate-pulse rounded-2xl bg-[#e5dfd3]" />
                  <p className="mt-4">工作流完成后，报告将在这里出现。</p>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
