"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  createResearchRun,
  listResearchRuns,
  type ResearchRun,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const exampleGoal =
  "调研学术界和工业界对 AI 代码生成工具的评测方法，并设计一份覆盖代码质量、安全性和开发效率的评测方案。";

const statusLabel: Record<ResearchRun["status"], string> = {
  queued: "等待中",
  running: "研究中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export default function Dashboard() {
  const router = useRouter();
  const [goal, setGoal] = useState(exampleGoal);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listResearchRuns()
      .then(setRuns)
      .catch(() => setError("无法读取研究历史，请确认后端已经启动。"))
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const run = await createResearchRun(goal);
      router.push("/research/" + run.id);
    } catch {
      setError("创建研究任务失败，请检查后端连接。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4f1e9] text-[#17231d]">
      <section className="border-b border-[#d8d3c7] bg-[#173f35] text-white">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="mb-10 flex items-center justify-between">
            <div className="text-lg font-semibold tracking-tight">ResearchFlow</div>
            <div className="rounded-full border border-white/25 px-3 py-1 text-xs text-white/75">
              M1 · LLM Planning
            </div>
          </div>
          <div className="max-w-3xl">
            <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-[#b9d9c7]">
              Evidence-first research workspace
            </p>
            <h1 className="text-4xl font-semibold leading-tight sm:text-6xl">
              从研究目标到可追溯的方案文档
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-white/70">
              将开放问题拆成研究任务，整合网页、论文与知识库证据，并实时展示研究过程。
            </p>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-10 lg:grid-cols-[1.35fr_0.85fr]">
        <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-semibold text-[#7b4f2f]">NEW RESEARCH</p>
          <h2 className="mt-2 text-2xl font-semibold">你想研究什么？</h2>
          <form className="mt-6" onSubmit={submit}>
            <textarea
              className="min-h-48 w-full resize-none rounded-2xl border border-[#cfc9bd] bg-[#fbfaf7] p-5 leading-7 outline-none transition focus:border-[#2f6f5e] focus:ring-4 focus:ring-[#2f6f5e]/10"
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              minLength={10}
              maxLength={4000}
              required
            />
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-[#6d746f]">
                规划阶段可调用真实 LLM；检索、分析和报告阶段当前仍为演示流程。
              </p>
              <button
                className="rounded-full bg-[#d96f32] px-6 py-3 font-semibold text-white transition hover:bg-[#bd5e2a] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={submitting || goal.trim().length < 10}
                type="submit"
              >
                {submitting ? "正在创建…" : "开始研究"}
              </button>
            </div>
          </form>
          {error && (
            <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}
        </section>

        <section className="rounded-3xl border border-[#d8d3c7] bg-[#ebe5d9] p-6 sm:p-8">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-sm font-semibold text-[#7b4f2f]">HISTORY</p>
              <h2 className="mt-2 text-2xl font-semibold">研究记录</h2>
            </div>
            <span className="text-sm text-[#6d746f]">{runs.length} 项</span>
          </div>

          <div className="mt-6 space-y-3">
            {loading && <p className="text-sm text-[#6d746f]">正在加载…</p>}
            {!loading && runs.length === 0 && (
              <div className="rounded-2xl border border-dashed border-[#bbb3a4] p-6 text-sm leading-6 text-[#6d746f]">
                还没有研究记录。创建第一个任务后，它会保存在本地 SQLite 数据库中。
              </div>
            )}
            {runs.map((run) => (
              <Link
                className="block rounded-2xl border border-[#d5cec0] bg-white p-4 transition hover:-translate-y-0.5 hover:border-[#8ea99d]"
                href={"/research/" + run.id}
                key={run.id}
              >
                <div className="flex items-start justify-between gap-4">
                  <h3 className="line-clamp-2 font-medium leading-6">{run.title}</h3>
                  <span className="shrink-0 rounded-full bg-[#edf3ef] px-2.5 py-1 text-xs font-medium text-[#2f6f5e]">
                    {statusLabel[run.status]}
                  </span>
                </div>
                <p className="mt-3 text-xs text-[#777c78]">
                  {run.completed_at ? "完成于 " : "更新于 "}
                  {formatDateTime(run.completed_at ?? run.updated_at)}
                </p>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#e7e2d8]">
                  <div
                    className="h-full rounded-full bg-[#d96f32]"
                    style={{ width: run.progress + "%" }}
                  />
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
