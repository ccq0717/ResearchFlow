import type { ResearchMaterials } from "@/lib/api";

interface ResearchMaterialsPanelProps {
  materials: ResearchMaterials | null;
}

export function ResearchMaterialsPanel({
  materials,
}: ResearchMaterialsPanelProps) {
  const sources = materials?.sources ?? [];
  const evidence = materials?.evidence ?? [];
  const sourceById = new Map(sources.map((source) => [source.id, source]));

  return (
    <section className="rounded-3xl border border-[#d8d3c7] bg-white p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">来源与证据</h2>
        <span className="text-xs text-[#777c78]">
          {sources.length} 来源 · {evidence.length} 证据
        </span>
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
