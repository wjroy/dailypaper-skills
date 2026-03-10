#!/usr/bin/env python3
"""Unified paper record schemas for daily-papers pipeline.

These dataclasses define the canonical JSON contracts across:
- Published channel (paper-fetcher metadata -> lite review -> PDF enrich -> rich review)
- Preprint channel (arXiv/bioRxiv fetch -> enrich -> rich review)
- Merge layer (rich reviewed pools -> notes/reader/MOC)

Design rule: fields that cannot be extracted must stay empty and be reported via
`missing_field_report` / `extraction_notes`; never fabricate values.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ChannelName = Literal["published", "preprint"]
ReviewDecisionLite = Literal["fetch_pdf", "hold", "skip"]
ReviewDecisionRich = Literal["must_read", "worth_reading", "skip"]


@dataclass
class RawPaperRecord:
    """Metadata-first unified record before LLM review.

    Field source notes:
    - identity fields: adapter-generated canonical IDs
    - metadata fields: upstream providers (paper-fetcher/arXiv/bioRxiv)
    - domain/match fields: local domain profile matching and ranking pipeline
    """

    paper_id: str
    channel: ChannelName
    source: str
    source_providers: list[str] = field(default_factory=list)
    source_id: str = ""

    title: str = ""
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)

    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    venue: str = ""
    publication_type: str = ""
    published_date: str = ""
    year: int | None = None

    citation_count: int = 0
    is_open_access: bool | None = None
    oa_url: str = ""
    oa_status: str = ""

    domain: str = ""
    matched_queries: list[str] = field(default_factory=list)
    matched_positive_keywords: list[str] = field(default_factory=list)
    matched_negative_keywords: list[str] = field(default_factory=list)
    matched_boost_keywords: list[str] = field(default_factory=list)

    provider_quality_score: float = 0.0
    metadata_completeness_score: float = 0.0
    relevance_score: float = 0.0
    freshness_score: float = 0.0
    publication_type_score: float = 0.0
    impact_score: float = 0.0
    accessibility_score: float = 0.0
    final_meta_score: float = 0.0

    metadata_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiteReviewPaperRecord(RawPaperRecord):
    """Record after metadata-first triage (no PDF dependence)."""

    review_tier: Literal["lite"] = "lite"
    evidence_scope: Literal["metadata_only"] = "metadata_only"
    lite_decision: ReviewDecisionLite = "hold"
    lite_confidence: float = 0.0
    lite_reasoning: str = ""
    recommended_for_pdf: bool = False


@dataclass
class RichReviewPaperRecord(LiteReviewPaperRecord):
    """Record after enrich + rich review (supports notes/reader downstream)."""

    review_tier: Literal["rich"] = "rich"
    evidence_scope: Literal["enriched_metadata_or_pdf"] = "enriched_metadata_or_pdf"

    local_pdf_paths: list[str] = field(default_factory=list)
    section_headers: list[str] = field(default_factory=list)
    figure_captions: list[str] = field(default_factory=list)
    table_captions: list[str] = field(default_factory=list)

    method_summary: str = ""
    method_names: list[str] = field(default_factory=list)
    experiment_clues: list[str] = field(default_factory=list)
    real_world_clues: list[str] = field(default_factory=list)
    simulation_clues: list[str] = field(default_factory=list)
    baseline_candidates: list[str] = field(default_factory=list)

    extraction_confidence: float = 0.0
    extraction_notes: list[str] = field(default_factory=list)
    missing_field_report: dict[str, str] = field(default_factory=dict)

    rich_decision: ReviewDecisionRich = "worth_reading"
    rich_confidence: float = 0.0
    core_method: str = ""
    compared_methods: list[str] = field(default_factory=list)
    borrowing_value: str = ""
    sharp_commentary: str = ""
    note_links: list[str] = field(default_factory=list)


FIELD_SOURCE_NOTES: dict[str, dict[str, str]] = {
    "RawPaperRecord": {
        "paper_id": "Adapter-generated canonical ID (prefer DOI, else source+source_id hash).",
        "source/source_providers": "Upstream retrieval adapters (paper-fetcher/arXiv/bioRxiv).",
        "title/abstract/authors/doi/url/venue": "Provider metadata returned by upstream APIs.",
        "matched_*": "Domain profile keyword matching in ranking stage.",
        "*_score/final_meta_score": "Metadata ranker output with weighted scoring formula.",
    },
    "LiteReviewPaperRecord": {
        "lite_decision/lite_reasoning": "review-lite output; must be based on metadata/abstract only.",
        "recommended_for_pdf": "Derived from lite decision and selection budget.",
    },
    "RichReviewPaperRecord": {
        "local_pdf_paths": "User-provided local PDFs / Zotero attachment paths.",
        "section_headers/figure_captions/table_captions": "PDF/preprint enrich extractors.",
        "method_* / experiment_*": "Enrich extractors from PDF/HTML content.",
        "missing_field_report": "Explicit extraction failures and reasons (no fabrication).",
        "rich_decision/*": "review-rich output grounded in enriched evidence.",
    },
}


def get_field_source_notes() -> dict[str, dict[str, str]]:
    """Return schema field source notes for docs and runtime introspection."""

    return FIELD_SOURCE_NOTES
