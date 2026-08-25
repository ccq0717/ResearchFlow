import html
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from researchflow.integrations.web.base import (
    SearchResult,
    WebDocument,
    WebResearchError,
)


class _StackExchangeClient:
    def __init__(
        self,
        *,
        base_url: str,
        site: str,
        timeout_seconds: float,
        user_agent: str,
        max_attempts: int,
        transport: httpx.AsyncBaseTransport | None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._site = site
        self._timeout = timeout_seconds
        self._headers = {"User-Agent": user_agent}
        self._max_attempts = max_attempts
        self._transport = transport

    async def request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    transport=self._transport,
                    headers=self._headers,
                ) as client:
                    response = await client.get(
                        f"{self._base_url}{path}",
                        params={"site": self._site, **params},
                    )
                    response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise TypeError("Stack Exchange response must be an object")
                if payload.get("error_id") is not None:
                    raise ValueError("Stack Exchange response contains an error")
                return payload
            except httpx.HTTPStatusError as error:
                last_error = error
                retryable = error.response.status_code == 429 or error.response.status_code >= 500
                if not retryable or attempt + 1 == self._max_attempts:
                    break
            except httpx.RequestError as error:
                last_error = error
                if attempt + 1 == self._max_attempts:
                    break
            except (TypeError, ValueError) as error:
                last_error = error
                break
        raise WebResearchError(
            "WEB_PROVIDER_UNAVAILABLE",
            "技术网页服务暂时不可用",
        ) from last_error


class StackExchangeSearchProvider:
    """通过 Stack Exchange API 搜索公开技术问答网页。"""

    def __init__(
        self,
        *,
        base_url: str,
        site: str,
        timeout_seconds: float,
        user_agent: str,
        max_attempts: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = _StackExchangeClient(
            base_url=base_url,
            site=site,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            max_attempts=max_attempts,
            transport=transport,
        )

    async def search(self, query: str, *, limit: int) -> tuple[SearchResult, ...]:
        payload = await self._client.request(
            "/search/advanced",
            {
                "q": query,
                "pagesize": limit,
                "order": "desc",
                "sort": "relevance",
            },
        )
        try:
            return tuple(
                SearchResult(
                    title=html.unescape(str(row["title"])),
                    url=str(row["link"]),
                    snippet="标签：" + "、".join(str(tag) for tag in row.get("tags", [])),
                )
                for row in payload["items"]
            )
        except (KeyError, TypeError) as error:
            raise WebResearchError(
                "SEARCH_INVALID_RESPONSE",
                "技术网页服务返回的数据格式不符合要求",
            ) from error


class StackExchangePageReader:
    """通过 Stack Exchange API 读取问题正文，避开页面抓取与脚本内容。"""

    _QUESTION_ID = re.compile(r"/questions/(\d+)")

    def __init__(
        self,
        *,
        base_url: str,
        site: str,
        timeout_seconds: float,
        user_agent: str,
        max_characters: int,
        max_attempts: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = _StackExchangeClient(
            base_url=base_url,
            site=site,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            max_attempts=max_attempts,
            transport=transport,
        )
        self._max_characters = max_characters

    async def read(self, result: SearchResult) -> WebDocument:
        match = self._QUESTION_ID.search(result.url)
        if match is None:
            raise WebResearchError("WEB_PAGE_INVALID_URL", "技术网页地址无法识别")
        payload = await self._client.request(
            f"/questions/{match.group(1)}",
            {"filter": "withbody"},
        )
        try:
            row = payload["items"][0]
            title = html.unescape(str(row["title"]))
            content = self._plain_text(str(row["body"]))
        except (IndexError, KeyError, TypeError) as error:
            raise WebResearchError(
                "WEB_PAGE_INVALID_RESPONSE",
                "技术网页正文格式不符合要求",
            ) from error
        if len(content) < 100:
            raise WebResearchError("WEB_PAGE_EMPTY", "技术网页没有足够的可读正文")
        return WebDocument(
            title=title,
            url=str(row.get("link") or result.url),
            content=content[: self._max_characters],
        )

    @staticmethod
    def _plain_text(value: str) -> str:
        soup = BeautifulSoup(value, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        return re.sub(r"\s+", " ", " ".join(soup.stripped_strings)).strip()
