import json
import re
from typing import Any

import httpx

from researchflow.integrations.web.base import (
    SearchResult,
    WebResearchError,
)


class ExaSearchProvider:
    """通过 Exa Search API 检索通用 Web，并返回可供证据提取的 highlights。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        user_agent: str,
        max_attempts: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/search"
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent,
            "x-api-key": api_key,
        }
        self._timeout = timeout_seconds
        self._max_attempts = max_attempts
        self._transport = transport

    async def search(self, query: str, *, limit: int) -> tuple[SearchResult, ...]:
        payload = await self._request(
            {
                "query": query,
                "type": "auto",
                "numResults": limit,
                "contents": {"highlights": True},
            }
        )
        try:
            rows = payload["results"]
            if not isinstance(rows, list):
                raise TypeError("Exa results must be a list")
            return tuple(self._parse_result(row) for row in rows)
        except (KeyError, TypeError, ValueError) as error:
            raise WebResearchError(
                "SEARCH_INVALID_RESPONSE",
                "网页搜索服务返回的数据格式不符合要求",
            ) from error

    async def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    transport=self._transport,
                    headers=self._headers,
                ) as client:
                    response = await client.post(self._endpoint, json=body)
                    response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise TypeError("Exa response must be an object")
                return payload
            except httpx.TimeoutException as error:
                if attempt + 1 == self._max_attempts:
                    raise WebResearchError(
                        "WEB_PROVIDER_TIMEOUT",
                        "网页搜索服务响应超时，请稍后重试",
                    ) from error
            except httpx.HTTPStatusError as error:
                status_code = error.response.status_code
                if status_code in {401, 403}:
                    raise WebResearchError(
                        "WEB_PROVIDER_AUTH_FAILED",
                        "网页搜索服务鉴权失败，请检查服务端配置",
                    ) from error
                if status_code == 429:
                    if attempt + 1 == self._max_attempts:
                        raise WebResearchError(
                            "WEB_PROVIDER_RATE_LIMITED",
                            "网页搜索额度已用尽或请求过于频繁，请稍后重试",
                        ) from error
                    continue
                if status_code >= 500:
                    if attempt + 1 == self._max_attempts:
                        raise WebResearchError(
                            "WEB_PROVIDER_UNAVAILABLE",
                            "网页搜索服务暂时不可用",
                        ) from error
                    continue
                raise WebResearchError(
                    "WEB_PROVIDER_REQUEST_REJECTED",
                    "网页搜索服务拒绝了本次请求",
                ) from error
            except httpx.RequestError as error:
                if attempt + 1 == self._max_attempts:
                    raise WebResearchError(
                        "WEB_PROVIDER_UNAVAILABLE",
                        "无法连接网页搜索服务",
                    ) from error
            except (json.JSONDecodeError, TypeError) as error:
                raise WebResearchError(
                    "SEARCH_INVALID_RESPONSE",
                    "网页搜索服务返回的数据格式不符合要求",
                ) from error
        raise AssertionError("Exa request loop exited without a result")

    @classmethod
    def _parse_result(cls, row: Any) -> SearchResult:
        if not isinstance(row, dict):
            raise TypeError("Exa result must be an object")
        raw_url = row["url"]
        if not isinstance(raw_url, str) or not raw_url.startswith(("https://", "http://")):
            raise ValueError("Exa result URL must be an HTTP URL")
        url = raw_url.strip()
        title = str(row.get("title") or url).strip()
        highlights = row.get("highlights") or []
        if not isinstance(highlights, list) or not all(
            isinstance(highlight, str) for highlight in highlights
        ):
            raise TypeError("Exa highlights must be a list of strings")
        content = "\n\n".join(
            cls._plain_text(highlight) for highlight in highlights if highlight.strip()
        ).strip()
        return SearchResult(
            title=title,
            url=url,
            snippet=content[:500],
            content=content or None,
            published_at=cls._optional_text(row.get("publishedDate")),
            author=cls._optional_text(row.get("author")),
        )

    @staticmethod
    def _plain_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
