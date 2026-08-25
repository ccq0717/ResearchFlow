import type { ResearchMaterials, ResearchSource } from "@/lib/api";

const sourceTypeLabels: Record<ResearchSource["source_type"], string> = {
  academic: "学术",
  official: "官方",
  industry: "工业",
  community: "社区",
  other: "其他",
};

interface ResearchMaterialsPanelProps {
  materials: ResearchMaterials | null;
}

export function ResearchMaterialsPanel({
  materials,
}: ResearchMaterialsPanelProps) {
  const sources = materials?.sources ?? [];
  const evidence = materials?.evidence ?? [];
  const claims = materials?.claims ?? [];
  const audit = materials?.citation_audit;
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const evidenceById = new Map(evidence.map((item) => [item.id, item]));

  return (
    <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-semibold">来源与证据</h2>
        <div className="text-right text-xs text-[#777c78]">
          <p>{sources.length} 来源 · {evidence.length} 证据 · {claims.length} 主张</p>
          {audit && audit.claim_count > 0 && (
            <p className="mt-1 font-semibold text-[#2f6f5e]">
              引用覆盖 {audit.coverage_percent}%
            </p>
          )}
        </div>
      </div>

      {sources.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-[#737a75]">
          真实网页研究模式会在这里展示已读取的来源和提取证据。
        </p>
      ) : (
        <div className="mt-5 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-[#7b4f2f]">网页来源</h3>
            <ul className="mt-3 space-y-3">
              {sources.map((source) => (
                <li className="rounded-2xl bg-[#f6f3ec] p-3" key={source.id}>
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="rounded-full bg-[#dfeae5] px-2 py-0.5 font-semibold text-[#2f6f5e]">
                      {sourceTypeLabels[source.source_type]}
                    </span>
                    {source.publisher && <span>{source.publisher}</span>}
                    {source.published_at && <span>{source.published_at.slice(0, 10)}</span>}
                  </div>
                  <a
                    className="text-sm font-medium text-[#2f6f5e] underline decoration-[#9cb8ac] underline-offset-2"
                    href={source.url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {source.title}
                  </a>
                  {source.snippet && (
                    <p className="mt-1 line-clamp-3 text-xs leading-5 text-[#737a75]">
                      {source.snippet}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-[#7b4f2f]">关键主张</h3>
            <ul className="mt-3 space-y-3">
              {claims.map((claim) => (
                <li className="rounded-2xl border border-[#d8d3c7] p-3" key={claim.id}>
                  <p className="text-xs font-semibold uppercase text-[#2f6f5e]">
                    {claim.id}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-[#354039]">{claim.text}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {claim.evidence_ids.map((evidenceId) => {
                      const item = evidenceById.get(evidenceId);
                      const source = item ? sourceById.get(item.source_id) : undefined;
                      return source ? (
                        <a
                          className="text-xs text-[#2f6f5e] underline"
                          href={source.url}
                          key={evidenceId}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {evidenceId} · {source.title}
                        </a>
                      ) : (
                        <span className="text-xs text-[#9a5540]" key={evidenceId}>
                          {evidenceId} · 来源缺失
                        </span>
                      );
                    })}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-[#7b4f2f]">提取证据</h3>
            <ul className="mt-3 space-y-3">
              {evidence.map((item) => {
                const source = sourceById.get(item.source_id);
                return (
                  <li
                    className="border-l-2 border-[#9cb8ac] pl-3 text-sm"
                    key={item.id}
                  >
                    <p className="leading-6 text-[#354039]">{item.summary}</p>
                    <blockquote className="mt-2 text-xs leading-5 text-[#737a75]">
                      “{item.excerpt}”
                    </blockquote>
                    {source && (
                      <a
                        className="mt-2 inline-block text-xs text-[#2f6f5e] underline"
                        href={source.url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        查看来源：{source.title}
                      </a>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}
