from researchflow.integrations.web.base import (
    SearchResult,
    WebDocument,
    WebResearchError,
)


class SearchResultPageReader:
    """读取 Search Provider 已提取的正文，避免工作流依赖具体供应商。"""

    def __init__(self, *, max_characters: int) -> None:
        self._max_characters = max_characters

    async def read(self, result: SearchResult) -> WebDocument:
        content = (result.content or "").strip()
        if not content:
            raise WebResearchError(
                "WEB_CONTENT_UNAVAILABLE",
                "网页搜索结果没有可读取的正文",
            )
        return WebDocument(
            title=result.title,
            url=result.url,
            content=content[: self._max_characters],
        )
