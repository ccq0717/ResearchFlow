from datetime import UTC, datetime
from urllib.parse import urlparse

from researchflow.domain.research import SourceType

_ACADEMIC_HOSTS = (
    "acm.org",
    "aclanthology.org",
    "arxiv.org",
    "ieee.org",
    "nature.com",
    "openreview.net",
    "proceedings.iclr.cc",
    "proceedings.neurips.cc",
    "science.org",
    "semanticscholar.org",
    "springer.com",
    "sciencedirect.com",
)
_OFFICIAL_HOSTS = ("etsi.org", "iso.org", "owasp.org", "w3.org")
_COMMUNITY_HOSTS = (
    "dev.to",
    "news.ycombinator.com",
    "reddit.com",
    "stackoverflow.com",
)
_OFFICIAL_HOST_PREFIXES = ("docs.", "developer.", "developers.")
_INDUSTRY_HOST_PREFIXES = ("blog.", "engineering.", "research.")


def classify_source(url: str) -> SourceType:
    """使用可解释的 URL 规则提供稳定分类；未知来源保守归为 other。"""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.lower()

    if _matches_host(host, _ACADEMIC_HOSTS) or host.endswith((".edu", ".ac.uk")):
        return SourceType.ACADEMIC
    if _matches_host(host, _COMMUNITY_HOSTS) or (
        host in {"github.com", "gitlab.com"} and ("/issues/" in path or "/discussions/" in path)
    ):
        return SourceType.COMMUNITY
    if (
        _matches_host(host, _OFFICIAL_HOSTS)
        or host.endswith((".gov", ".gov.cn"))
        or host.startswith(_OFFICIAL_HOST_PREFIXES)
        or host in {"github.com", "gitlab.com"}
    ):
        return SourceType.OFFICIAL
    if host.startswith(_INDUSTRY_HOST_PREFIXES) or any(
        marker in path for marker in ("/blog/", "/blogs/")
    ):
        return SourceType.INDUSTRY
    return SourceType.OTHER


def infer_publisher(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host or None


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _matches_host(host: str, candidates: tuple[str, ...]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)
