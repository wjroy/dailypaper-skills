#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
SHARED_DIR = DAILY_PAPERS_DIR.parent / "_shared"
ADAPTERS_DIR = DAILY_PAPERS_DIR / "adapters"
RANKING_DIR = DAILY_PAPERS_DIR / "ranking"
ENRICH_DIR = DAILY_PAPERS_DIR / "enrich"
SCHEMAS_DIR = DAILY_PAPERS_DIR / "schemas"

for p in (SHARED_DIR, ADAPTERS_DIR, RANKING_DIR, ENRICH_DIR, SCHEMAS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from arxiv_adapter import fetch_arxiv_records
from domain_ranker import provider_preference_multiplier, score_relevance
from metadata_ranker import compute_final_meta_score
from paper_records import RichReviewPaperRecord
from preprint_enrich_arxiv import enrich_arxiv_preprint
from user_config import (
    active_domain,
    active_domain_profile,
    preprint_channel_config,
)


TMP_DIR = Path("/tmp")
RAW_PATH = TMP_DIR / "preprint_raw.json"
ENRICHED_PATH = TMP_DIR / "preprint_enriched.json"
REVIEW_RICH_PATH = TMP_DIR / "preprint_review_rich_20.json"


def _safe_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def resolve_preprint_source() -> str:
    return "arxiv"


def _score_and_filter(
    records: list[dict], profile: dict, domain_name: str
) -> list[dict]:
    out: list[dict] = []
    for record in records:
        dm = score_relevance(
            record.get("title", ""), record.get("abstract", ""), profile
        )
        if dm.matched_negative_keywords and dm.relevance_score <= 0.2:
            continue

        final_meta_score, components = compute_final_meta_score(
            record=record,
            relevance_score=dm.relevance_score,
            domain_multiplier=provider_preference_multiplier(
                record.get("source_providers", []), profile
            ),
        )

        item = dict(record)
        item.update(
            {
                "domain": domain_name,
                "matched_queries": dm.matched_queries,
                "matched_positive_keywords": dm.matched_positive_keywords,
                "matched_negative_keywords": dm.matched_negative_keywords,
                "matched_boost_keywords": dm.matched_boost_keywords,
                "relevance_score": components["relevance_score"],
                "freshness_score": components["freshness_score"],
                "provider_quality_score": components["provider_quality_score"],
                "metadata_completeness_score": components[
                    "metadata_completeness_score"
                ],
                "publication_type_score": components["publication_type_score"],
                "impact_score": components["impact_score"],
                "accessibility_score": components["accessibility_score"],
                "final_meta_score": final_meta_score,
            }
        )
        out.append(item)

    out.sort(key=lambda x: x.get("final_meta_score", 0.0), reverse=True)
    return out


def _enrich(records: list[dict], source: str) -> list[dict]:
    enriched: list[dict] = []
    for record in records:
        enriched.append(enrich_arxiv_preprint(record))
    return enriched


def _to_rich_review(records: list[dict], rich_n: int) -> list[RichReviewPaperRecord]:
    top = records[: max(1, rich_n)]
    out: list[RichReviewPaperRecord] = []
    for rec in top:
        score = float(rec.get("final_meta_score", 0.0))
        if score >= 0.72:
            decision = "must_read"
        elif score >= 0.5:
            decision = "worth_reading"
        else:
            decision = "skip"

        record = RichReviewPaperRecord(
            paper_id=rec.get("paper_id", ""),
            channel="preprint",
            source=rec.get("source", ""),
            source_providers=list(rec.get("source_providers", [])),
            source_id=rec.get("source_id", ""),
            title=rec.get("title", ""),
            abstract=rec.get("abstract", ""),
            authors=list(rec.get("authors", [])),
            affiliations=list(rec.get("affiliations", [])),
            doi=rec.get("doi", ""),
            url=rec.get("url", ""),
            pdf_url=rec.get("pdf_url", ""),
            venue=rec.get("venue", ""),
            publication_type=rec.get("publication_type", "preprint"),
            published_date=rec.get("published_date", ""),
            year=rec.get("year"),
            citation_count=int(rec.get("citation_count", 0)),
            is_open_access=rec.get("is_open_access"),
            oa_url=rec.get("oa_url", ""),
            oa_status=rec.get("oa_status", ""),
            domain=rec.get("domain", ""),
            matched_queries=list(rec.get("matched_queries", [])),
            matched_positive_keywords=list(rec.get("matched_positive_keywords", [])),
            matched_negative_keywords=list(rec.get("matched_negative_keywords", [])),
            matched_boost_keywords=list(rec.get("matched_boost_keywords", [])),
            provider_quality_score=float(rec.get("provider_quality_score", 0.0)),
            metadata_completeness_score=float(
                rec.get("metadata_completeness_score", 0.0)
            ),
            relevance_score=float(rec.get("relevance_score", 0.0)),
            freshness_score=float(rec.get("freshness_score", 0.0)),
            publication_type_score=float(rec.get("publication_type_score", 0.0)),
            impact_score=float(rec.get("impact_score", 0.0)),
            accessibility_score=float(rec.get("accessibility_score", 0.0)),
            final_meta_score=float(rec.get("final_meta_score", 0.0)),
            metadata_trace=rec.get("metadata_trace", {}),
            review_tier="rich",
            evidence_scope="enriched_metadata_or_pdf",
            lite_decision="hold",
            lite_confidence=max(0.2, min(1.0, score)),
            lite_reasoning="preprint channel enters rich review directly after enrich",
            recommended_for_pdf=False,
            local_pdf_paths=[],
            zotero_attachment_paths=[],
            preferred_fulltext_input_type=(
                "arxiv_url" if rec.get("source") == "arxiv" else "pdf_url"
            ),
            preferred_fulltext_input_value=(
                rec.get("url", "")
                if rec.get("source") == "arxiv"
                else rec.get("pdf_url", "") or rec.get("url", "")
            ),
            section_headers=list(rec.get("section_headers", [])),
            figure_captions=list(rec.get("figure_captions", [])),
            table_captions=list(rec.get("table_captions", [])),
            method_summary=rec.get("method_summary", ""),
            method_names=list(rec.get("method_names", [])),
            experiment_clues=list(rec.get("experiment_clues", [])),
            real_world_clues=list(rec.get("real_world_clues", [])),
            simulation_clues=list(rec.get("simulation_clues", [])),
            baseline_candidates=list(rec.get("baseline_candidates", [])),
            extraction_confidence=float(rec.get("extraction_confidence", 0.0)),
            extraction_notes=list(rec.get("extraction_notes", [])),
            missing_field_report=dict(rec.get("missing_field_report", {})),
            rich_decision=decision,
            rich_confidence=max(0.25, min(1.0, score)),
            core_method=rec.get("method_summary", "")[:300],
            compared_methods=list(rec.get("baseline_candidates", [])),
            borrowing_value="Derived from enriched metadata cues; verify with full text before citation-level claims.",
            sharp_commentary="Auto-generated rich triage from enriched preprint signals; not a full manual review.",
            inspiration_notes="优先借鉴可迁移的方法组件；涉及具体结果时回看原文细节。",
            note_links=[],
        )
        out.append(record)
    return out


def run() -> dict:
    cfg = preprint_channel_config()
    if not cfg.get("enabled", True):
        _safe_write_json(RAW_PATH, [])
        _safe_write_json(ENRICHED_PATH, [])
        _safe_write_json(REVIEW_RICH_PATH, [])
        return {"status": "disabled"}

    source = resolve_preprint_source()
    profile = active_domain_profile()
    domain_name = active_domain()
    queries = profile.get("queries", []) or [domain_name.replace("_", " ")]
    query = queries[0]

    sources_cfg = cfg.get("sources", {}) or {}
    a_cfg = sources_cfg.get("arxiv", {}) or {}
    raw_records = fetch_arxiv_records(
        query=query,
        categories=list(a_cfg.get("categories", [])),
        max_results=int(a_cfg.get("max_results", 200)),
        sort_by=str(a_cfg.get("sort_by", "submittedDate")),
    )

    scored = _score_and_filter(raw_records, profile=profile, domain_name=domain_name)
    _safe_write_json(RAW_PATH, scored)

    enriched = _enrich(scored, source=source)
    _safe_write_json(ENRICHED_PATH, enriched)

    rich_n = int(cfg.get("rich_n", 20))
    rich_reviewed = _to_rich_review(enriched, rich_n=rich_n)
    _safe_write_json(REVIEW_RICH_PATH, [asdict(item) for item in rich_reviewed])

    return {
        "status": "ok",
        "source": source,
        "domain": domain_name,
        "counts": {
            "raw": len(scored),
            "enriched": len(enriched),
            "review_rich": len(rich_reviewed),
        },
        "outputs": {
            "preprint_raw": str(RAW_PATH),
            "preprint_enriched": str(ENRICHED_PATH),
            "preprint_review_rich_20": str(REVIEW_RICH_PATH),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
