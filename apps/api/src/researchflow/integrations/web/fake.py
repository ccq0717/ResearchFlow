from hashlib import sha256

from researchflow.integrations.web.base import SearchResult, WebDocument


class FakeSearchProvider:
    """不访问网络的确定性搜索 adapter。"""

    async def search(self, query: str, *, limit: int) -> tuple[SearchResult, ...]:
        query_id = sha256(query.encode("utf-8")).hexdigest()[:12]
        normalized = query.lower()
        if "benchmark" in normalized or "dataset" in normalized:
            host = "arxiv.org"
            author = "Research Benchmark Team"
        elif "metric" in normalized:
            host = "docs.example.test"
            author = "Example Standards Group"
        else:
            host = "engineering.example.test"
            author = "Example Engineering"
        return tuple(
            SearchResult(
                title=f"{query}：公开资料 {index}",
                url=f"https://{host}/research/{query_id}/{index}",
                snippet=f"关于“{query}”的公开资料摘要 {index}。",
                published_at="2026-07-01T00:00:00Z",
                author=author,
            )
            for index in range(1, limit + 1)
        )


class FakeWebPageReader:
    """根据搜索结果生成可供证据提取的固定正文。"""

    async def read(self, result: SearchResult) -> WebDocument:
        return WebDocument(
            title=result.title,
            url=result.url,
            content=(
                f"{result.title}。{result.snippet}"
                "该资料说明评测应同时考虑任务完成率、代码质量、安全性与开发效率，"
                "并通过可复现实验和人工审查交叉验证结果。"
            ),
        )
