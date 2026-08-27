"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import {
  ApiError,
  archiveResearchRun,
  createDemoSession,
  createResearchRun,
  deleteKnowledgeDocument,
  deleteResearchRun,
  listKnowledgeDocuments,
  listResearchRuns,
  reprocessKnowledgeDocument,
  renameResearchRun,
  uploadKnowledgeDocument,
  type KnowledgeDocument,
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

const documentStatusLabel: Record<KnowledgeDocument["status"], string> = {
  processing: "处理中",
  ready: "可使用",
  failed: "处理失败",
};

export default function Dashboard() {
  const router = useRouter();
  const [goal, setGoal] = useState(exampleGoal);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accessRequired, setAccessRequired] = useState(false);
  const [accessCode, setAccessCode] = useState("");
  const [unlocking, setUnlocking] = useState(false);

  useEffect(() => {
    Promise.all([listResearchRuns(showArchived), listKnowledgeDocuments()])
      .then(([nextRuns, nextDocuments]) => {
        setRuns(nextRuns);
        setDocuments(nextDocuments);
      })
      .catch((cause: unknown) => {
        if (cause instanceof ApiError && cause.status === 401) {
          setAccessRequired(true);
        } else {
          setError("无法读取研究历史，请确认后端已经启动。");
        }
      })
      .finally(() => setLoading(false));
  }, [showArchived]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const run = await createResearchRun(goal, selectedDocumentIds);
      router.push("/research/" + run.id);
    } catch {
      setError("创建研究任务失败，请检查后端连接。");
    } finally {
      setSubmitting(false);
    }
  }

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const document = await uploadKnowledgeDocument(file);
      setDocuments((current) => [
        document,
        ...current.filter((item) => item.id !== document.id),
      ]);
    } catch {
      setError("上传知识文档失败，请检查格式、体积和后端状态。");
    } finally {
      setUploading(false);
    }
  }

  async function removeDocument(documentId: string) {
    if (!window.confirm("删除该文档及其分块？已生成报告中的证据快照不会被删除。")) return;
    setError(null);
    try {
      await deleteKnowledgeDocument(documentId);
      setDocuments((current) => current.filter((item) => item.id !== documentId));
      setSelectedDocumentIds((current) => current.filter((id) => id !== documentId));
    } catch {
      setError("删除知识文档失败。");
    }
  }

  async function reprocessDocument(documentId: string) {
    setError(null);
    try {
      const document = await reprocessKnowledgeDocument(documentId);
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? document : item)),
      );
    } catch {
      setError("重新处理知识文档失败。");
    }
  }

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  async function renameRun(run: ResearchRun) {
    const title = window.prompt("输入新的研究记录标题", run.title)?.trim();
    if (!title || title === run.title) return;
    try {
      const updated = await renameResearchRun(run.id, title);
      setRuns((current) => current.map((item) => (item.id === run.id ? updated : item)));
    } catch {
      setError("重命名研究记录失败。");
    }
  }

  async function toggleArchive(run: ResearchRun) {
    try {
      const updated = await archiveResearchRun(run.id, !run.archived);
      setRuns((current) =>
        showArchived
          ? current.map((item) => (item.id === run.id ? updated : item))
          : current.filter((item) => item.id !== run.id),
      );
    } catch {
      setError("归档研究记录失败；运行中的任务不能归档。");
    }
  }

  async function removeRun(run: ResearchRun) {
    if (!window.confirm("永久删除该研究记录及其中间材料？此操作无法撤销。")) return;
    try {
      await deleteResearchRun(run.id);
      setRuns((current) => current.filter((item) => item.id !== run.id));
    } catch {
      setError("删除研究记录失败；请先等待任务结束或取消任务。");
    }
  }

  async function unlockDemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUnlocking(true);
    setError(null);
    try {
      await createDemoSession(accessCode);
      window.location.reload();
    } catch {
      setError("访问码无效，请重新输入。");
      setUnlocking(false);
    }
  }

  if (accessRequired) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f4f1e9] p-6 text-[#17231d]">
        <form
          className="w-full max-w-md rounded-3xl border border-[#d8d3c7] bg-white p-8 shadow-sm"
          onSubmit={unlockDemo}
        >
          <p className="text-sm font-semibold text-[#7b4f2f]">PROTECTED DEMO</p>
          <h1 className="mt-2 text-3xl font-semibold">访问 ResearchFlow</h1>
          <p className="mt-3 text-sm leading-6 text-[#6d746f]">
            请输入作品集演示访问码。访问码只发送给后端，不会写入浏览器包。
          </p>
          <input
            aria-label="演示访问码"
            autoComplete="current-password"
            className="mt-6 w-full rounded-2xl border border-[#cfc9bd] px-4 py-3 outline-none focus:border-[#2f6f5e]"
            onChange={(event) => setAccessCode(event.target.value)}
            required
            type="password"
            value={accessCode}
          />
          <button
            className="mt-4 w-full rounded-full bg-[#2f6f5e] px-5 py-3 font-semibold text-white disabled:opacity-50"
            disabled={unlocking}
            type="submit"
          >
            {unlocking ? "正在验证…" : "进入演示"}
          </button>
          {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f4f1e9] text-[#17231d]">
      <section className="border-b border-[#d8d3c7] bg-[#173f35] text-white">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="mb-10 flex items-center justify-between">
            <div className="text-lg font-semibold tracking-tight">ResearchFlow</div>
            <div className="rounded-full border border-white/25 px-3 py-1 text-xs text-white/75">
              Local Knowledge + Web
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
              从研究目标生成结构化计划，检索开放 Web 中的公开资料，并展示可恢复的来源、证据与研究过程。
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
                已选择 {selectedDocumentIds.length} 个本地文档；LangGraph 模式会联合 Exa
                公开网页形成证据。
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
            <label className="flex items-center gap-2 text-sm text-[#6d746f]">
              <input
                checked={showArchived}
                className="accent-[#2f6f5e]"
                onChange={(event) => setShowArchived(event.target.checked)}
                type="checkbox"
              />
              显示归档
            </label>
          </div>

          <div className="mt-6 space-y-3">
            {loading && <p className="text-sm text-[#6d746f]">正在加载…</p>}
            {!loading && runs.length === 0 && (
              <div className="rounded-2xl border border-dashed border-[#bbb3a4] p-6 text-sm leading-6 text-[#6d746f]">
                还没有研究记录。创建第一个任务后，它会保存在本地 SQLite 数据库中。
              </div>
            )}
            {runs.map((run) => (
              <article
                className="rounded-2xl border border-[#d5cec0] bg-white p-4"
                key={run.id}
              >
                <div className="flex items-start justify-between gap-4">
                  <Link
                    className="line-clamp-2 font-medium leading-6 hover:text-[#2f6f5e] hover:underline"
                    href={"/research/" + run.id}
                  >
                    {run.title}
                  </Link>
                  <span className="shrink-0 rounded-full bg-[#edf3ef] px-2.5 py-1 text-xs font-medium text-[#2f6f5e]">
                    {run.archived ? "已归档" : statusLabel[run.status]}
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
                <div className="mt-3 flex gap-3 text-xs">
                  <button className="underline" onClick={() => renameRun(run)} type="button">
                    重命名
                  </button>
                  <button className="underline" onClick={() => toggleArchive(run)} type="button">
                    {run.archived ? "取消归档" : "归档"}
                  </button>
                  <button
                    className="text-[#9a5540] underline"
                    onClick={() => removeRun(run)}
                    type="button"
                  >
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6 shadow-sm sm:p-8 lg:col-span-2">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-[#7b4f2f]">LOCAL KNOWLEDGE</p>
              <h2 className="mt-2 text-2xl font-semibold">本地知识库</h2>
              <p className="mt-2 text-sm text-[#6d746f]">
                支持 PDF、Markdown 和 UTF-8 纯文本；体积与数量限制由后端配置。
              </p>
            </div>
            <label className="cursor-pointer rounded-full bg-[#2f6f5e] px-5 py-3 text-center text-sm font-semibold text-white hover:bg-[#275d4f]">
              {uploading ? "正在处理…" : "上传文档"}
              <input
                accept=".pdf,.md,.markdown,.txt"
                className="sr-only"
                disabled={uploading}
                onChange={uploadDocument}
                type="file"
              />
            </label>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {!loading && documents.length === 0 && (
              <p className="text-sm text-[#6d746f]">尚未上传本地资料。</p>
            )}
            {documents.map((document) => (
              <article
                className="rounded-2xl border border-[#d8d3c7] bg-[#fbfaf7] p-4"
                key={document.id}
              >
                <div className="flex items-start gap-3">
                  <input
                    aria-label={`选择 ${document.original_filename}`}
                    checked={selectedDocumentIds.includes(document.id)}
                    className="mt-1 h-4 w-4 accent-[#2f6f5e]"
                    disabled={document.status !== "ready"}
                    onChange={() => toggleDocument(document.id)}
                    type="checkbox"
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-medium">{document.original_filename}</h3>
                    <p className="mt-1 text-xs text-[#6d746f]">
                      {documentStatusLabel[document.status]} · {document.chunk_count} 个片段 ·{" "}
                      {(document.size_bytes / 1024).toFixed(1)} KB
                    </p>
                    {document.error_message && (
                      <p className="mt-2 text-xs leading-5 text-[#9a5540]">
                        {document.error_message}
                      </p>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex gap-3 text-xs">
                  <button
                    className="text-[#2f6f5e] underline"
                    onClick={() => reprocessDocument(document.id)}
                    type="button"
                  >
                    重新处理
                  </button>
                  <button
                    className="text-[#9a5540] underline"
                    onClick={() => removeDocument(document.id)}
                    type="button"
                  >
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
