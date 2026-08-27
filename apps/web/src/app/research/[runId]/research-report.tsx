import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

type ResearchReportProps = {
  markdown: string;
};

function normalizeModelMarkdown(markdown: string) {
  let fence: "```" | "~~~" | null = null;

  return markdown
    .split("\n")
    .map((line) => {
      const marker = line.match(/^\s*(```|~~~)/)?.[1] as "```" | "~~~" | undefined;
      if (marker) {
        fence = fence === marker ? null : fence ?? marker;
        return line;
      }
      if (fence) return line;

      if (/^\s*\\[\[\]]\s*$/.test(line)) {
        return line.replace(/\\[\[\]]/, () => "$$");
      }

      return line
        .replace(/\\\((.+?)\\\)/g, (_, expression: string) => `$${expression}$`)
        .replace(
          /(\*\*[^*\r\n]*?[：:；;，,。.！？!?])\*\*(?=[\p{L}\p{N}])/gu,
          "$1** ",
        );
    })
    .join("\n");
}

function ExternalLink({
  href,
  children,
  ...props
}: ComponentPropsWithoutRef<"a">) {
  return (
    <a
      {...props}
      className="font-medium text-[#2f6f5e] underline decoration-[#8fb3a5] underline-offset-2 hover:text-[#1f5144]"
      href={href}
      rel="noreferrer noopener"
      target="_blank"
    >
      {children}
    </a>
  );
}

export function ResearchReport({ markdown }: ResearchReportProps) {
  const normalizedMarkdown = normalizeModelMarkdown(markdown);

  return (
    <article className="mt-6 text-[15px] leading-7 text-[#354039]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-5 mt-1 text-3xl font-semibold leading-tight text-[#17231d]">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-3 mt-9 border-b border-[#e5e0d6] pb-2 text-2xl font-semibold text-[#173f35]">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-7 text-xl font-semibold text-[#294f44]">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mb-2 mt-6 text-lg font-semibold text-[#294f44]">
              {children}
            </h4>
          ),
          p: ({ children }) => <p className="my-4">{children}</p>,
          ul: ({ children }) => (
            <ul className="my-4 list-disc space-y-2 pl-6">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-4 list-decimal space-y-2 pl-6">{children}</ol>
          ),
          li: ({ children }) => <li className="pl-1">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="my-5 border-l-4 border-[#a7b8af] bg-[#f5f2eb] px-5 py-1 text-[#53605a]">
              {children}
            </blockquote>
          ),
          a: ExternalLink,
          table: ({ children }) => (
            <div className="my-6 overflow-x-auto rounded-xl border border-[#d8d3c7]">
              <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#edf3ef] text-[#173f35]">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-[#d8d3c7] px-4 py-3 font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-[#e5e0d6] px-4 py-3 align-top">
              {children}
            </td>
          ),
          pre: ({ children }) => (
            <pre className="my-5 overflow-x-auto rounded-xl bg-[#17231d] p-4 text-sm leading-6 text-[#eef5f1]">
              {children}
            </pre>
          ),
          code: ({ children, className }) =>
            className ? (
              <code className={className}>{children}</code>
            ) : (
              <code className="rounded bg-[#ece8df] px-1.5 py-0.5 font-mono text-[0.9em] text-[#704326]">
                {children}
              </code>
            ),
          hr: () => <hr className="my-8 border-[#d8d3c7]" />,
          strong: ({ children }) => (
            <strong className="font-semibold text-[#17231d]">{children}</strong>
          ),
        }}
      >
        {normalizedMarkdown}
      </ReactMarkdown>
    </article>
  );
}
