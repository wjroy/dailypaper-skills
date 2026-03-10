#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime, timezone


WEIGHTS = {
    "relevance_score": 0.40,
    "freshness_score": 0.15,
    "provider_quality_score": 0.10,
    "metadata_completeness_score": 0.10,
    "publication_type_score": 0.10,
    "impact_score": 0.10,
    "accessibility_score": 0.05,
}


PROVIDER_QUALITY = {
    "crossref": 1.0,
    "openalex": 0.95,
    "semantic_scholar": 0.9,
    "pubmed": 0.95,
    "europe_pmc": 0.9,
    "arxiv": 0.75,
    "biorxiv": 0.75,
    "unpaywall": 0.8,
}


PUBLICATION_TYPE_SCORE = {
    "journal-article": 1.0,
    "article": 1.0,
    "review-article": 0.9,
    "conference-paper": 0.85,
    "proceedings-article": 0.85,
    "preprint": 0.65,
}


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            if fmt == "%Y":
                return dt.replace(month=1, day=1)
            if fmt == "%Y-%m":
                return dt.replace(day=1)
            return dt
        except ValueError:
            continue
    return None


def compute_freshness_score(published_date: str, year: int | None) -> float:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dt = _parse_date(published_date)
    if dt is None and year:
        dt = datetime(year=year, month=1, day=1)
    if dt is None:
        return 0.2

    age_days = max(0, (now - dt).days)
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.85
    if age_days <= 180:
        return 0.7
    if age_days <= 365:
        return 0.5
    if age_days <= 3 * 365:
        return 0.3
    return 0.15


def compute_provider_quality_score(source_providers: list[str]) -> float:
    if not source_providers:
        return 0.25
    values = [PROVIDER_QUALITY.get(p, 0.6) for p in source_providers]
    # multi-provider hit bonus (metadata consistency signal)
    bonus = 0.05 if len(set(source_providers)) > 1 else 0.0
    return max(0.0, min(1.0, sum(values) / len(values) + bonus))


def compute_metadata_completeness_score(record: dict) -> float:
    checks = [
        bool(record.get("title")),
        bool(record.get("abstract")),
        bool(record.get("authors")),
        bool(record.get("doi")),
        bool(record.get("venue")),
        bool(record.get("published_date") or record.get("year")),
        bool(record.get("url")),
    ]
    return sum(1 for item in checks if item) / len(checks)


def compute_publication_type_score(publication_type: str) -> float:
    ptype = (publication_type or "").strip().lower()
    if not ptype:
        return 0.4
    return PUBLICATION_TYPE_SCORE.get(ptype, 0.6)


def compute_impact_score(citation_count: int, year: int | None) -> float:
    cites = max(0, int(citation_count or 0))
    if cites == 0:
        return 0.2
    if cites <= 5:
        return 0.35
    if cites <= 20:
        return 0.55
    if cites <= 100:
        return 0.75
    return 0.95


def compute_accessibility_score(record: dict) -> float:
    has_pdf = bool(record.get("pdf_url"))
    is_oa = bool(record.get("is_open_access"))
    has_oa_url = bool(record.get("oa_url"))
    if has_pdf and (is_oa or has_oa_url):
        return 1.0
    if has_pdf:
        return 0.8
    if is_oa or has_oa_url:
        return 0.75
    return 0.35


def compute_final_meta_score(
    record: dict, relevance_score: float, domain_multiplier: float = 1.0
) -> tuple[float, dict]:
    freshness_score = compute_freshness_score(
        record.get("published_date", ""), record.get("year")
    )
    provider_quality_score = compute_provider_quality_score(
        record.get("source_providers", [])
    )
    metadata_completeness_score = compute_metadata_completeness_score(record)
    publication_type_score = compute_publication_type_score(
        record.get("publication_type", "")
    )
    impact_score = compute_impact_score(
        record.get("citation_count", 0), record.get("year")
    )
    accessibility_score = compute_accessibility_score(record)

    score_components = {
        "relevance_score": max(0.0, min(1.0, relevance_score * domain_multiplier)),
        "freshness_score": freshness_score,
        "provider_quality_score": provider_quality_score,
        "metadata_completeness_score": metadata_completeness_score,
        "publication_type_score": publication_type_score,
        "impact_score": impact_score,
        "accessibility_score": accessibility_score,
    }

    final_meta_score = 0.0
    for key, value in score_components.items():
        final_meta_score += WEIGHTS[key] * value

    return max(0.0, min(1.0, final_meta_score)), score_components
