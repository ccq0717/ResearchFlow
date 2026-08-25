import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ResearchReport } from "./research-report";

describe("ResearchReport", () => {
  it("renders headings, GFM tables, lists and safe external links", () => {
    const html = renderToStaticMarkup(
      <ResearchReport
        markdown={`# 研究结论

| 指标 | 结果 |
| --- | --- |
| 正确率 | 80% |

- [来源](https://example.com/report)
`}
      />,
    );

    expect(html).toContain("<h1");
    expect(html).toContain("<table");
    expect(html).toContain("<li");
    expect(html).toContain('href="https://example.com/report"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noreferrer noopener"');
  });

  it("does not render raw HTML or unsafe link protocols", () => {
    const html = renderToStaticMarkup(
      <ResearchReport
        markdown={'<script>alert("xss")</script>\n\n[危险链接](javascript:alert(1))'}
      />,
    );

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("javascript:");
  });
});
