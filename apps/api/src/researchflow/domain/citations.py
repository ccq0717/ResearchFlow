from researchflow.domain.research import CitationAudit, Claim, Evidence, Source, SourceType


def build_citation_audit(
    claims: tuple[Claim, ...],
    evidence: tuple[Evidence, ...],
    sources: tuple[Source, ...],
) -> CitationAudit:
    """根据完整的 Claim—Evidence—Source 链路计算引用覆盖率。"""
    evidence_by_id = {item.id: item for item in evidence}
    source_ids = {source.id for source in sources}
    unsupported = tuple(
        claim.id
        for claim in claims
        if not claim.evidence_ids
        or not all(
            evidence_id in evidence_by_id and evidence_by_id[evidence_id].source_id in source_ids
            for evidence_id in claim.evidence_ids
        )
    )
    supported_count = len(claims) - len(unsupported)
    counts = {source_type: 0 for source_type in SourceType}
    for source in sources:
        counts[source.source_type] += 1
    return CitationAudit(
        claim_count=len(claims),
        supported_claim_count=supported_count,
        coverage_percent=round(supported_count / len(claims) * 100) if claims else 0,
        unsupported_claim_ids=unsupported,
        source_type_counts=counts,
    )
