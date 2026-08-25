from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    content: str | None = None
    published_at: str | None = None
    author: str | None = None


@dataclass(frozen=True, slots=True)
class WebDocument:
    title: str
    url: str
    content: str


class WebResearchError(Exception):
    """可安全展示给用户的搜索或网页读取错误。"""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class SearchProvider(Protocol):
    """把研究查询转换成候选网页。"""

    async def search(self, query: str, *, limit: int) -> tuple[SearchResult, ...]: ...


class WebPageReader(Protocol):
    """读取一个候选网页并返回清洗后的正文。"""

    async def read(self, result: SearchResult) -> WebDocument: ...
