import asyncio
import json
import sys
from dataclasses import asdict, dataclass

from researchflow.core.config import Settings
from researchflow.domain.research import SourceType
from researchflow.domain.source_quality import classify_source
from researchflow.integrations.web.exa import ExaSearchProvider


@dataclass(frozen=True, slots=True)
class CoverageQuery:
    id: str
    expected_type: SourceType
    query: str


QUERIES = (
    CoverageQuery(
        id="academic",
        expected_type=SourceType.ACADEMIC,
        query=(
            "peer reviewed papers and public benchmarks for evaluating AI code generation "
            "systems including HumanEval MBPP and SWE-bench"
        ),
    ),
    CoverageQuery(
        id="official",
        expected_type=SourceType.OFFICIAL,
        query=(
            "official documentation and public standards for evaluating AI coding assistants "
            "code correctness security and maintainability"
        ),
    ),
    CoverageQuery(
        id="industry",
        expected_type=SourceType.INDUSTRY,
        query=(
            "engineering blogs and industry studies measuring AI coding assistant developer "
            "productivity code quality and developer experience"
        ),
    ),
)


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = Settings()
    if settings.web_search_provider != "exa":
        raise SystemExit("覆盖度评测当前只支持 RESEARCHFLOW_WEB_SEARCH_PROVIDER=exa")
    if settings.web_search_api_key is None:
        raise SystemExit("请先设置 RESEARCHFLOW_WEB_SEARCH_API_KEY")

    provider = ExaSearchProvider(
        base_url=str(settings.web_search_base_url),
        api_key=settings.web_search_api_key.get_secret_value(),
        timeout_seconds=settings.web_request_timeout_seconds,
        user_agent=settings.web_user_agent,
    )
    evaluations = []
    for item in QUERIES:
        results = await provider.search(item.query, limit=5)
        normalized = [
            {
                "title": result.title,
                "url": result.url,
                "source_type": classify_source(result.url),
                "author": result.author,
                "published_at": result.published_at,
            }
            for result in results
        ]
        matching = sum(row["source_type"] == item.expected_type for row in normalized)
        evaluations.append(
            {
                **asdict(item),
                "matching_count": matching,
                "passed": matching >= 1,
                "results": normalized,
            }
        )

    payload = {
        "criteria": "每类固定查询的前 5 个结果中至少包含 1 个预期类型来源",
        "passed": all(item["passed"] for item in evaluations),
        "evaluations": evaluations,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
