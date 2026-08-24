interface ResearchErrorPanelProps {
  code: string | null;
  message: string | null;
}

export function ResearchErrorPanel({
  code,
  message,
}: ResearchErrorPanelProps) {
  return (
    <div
      aria-live="polite"
      className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5 text-red-950"
      role="alert"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.12em] text-red-700">
        研究任务执行失败
      </p>
      <p className="mt-3 leading-7">
        {message ?? "研究工作流未能完成，请检查配置后重新创建任务。"}
      </p>
      {code && (
        <p className="mt-3 font-mono text-xs text-red-700">
          错误代码：{code}
        </p>
      )}
    </div>
  );
}
