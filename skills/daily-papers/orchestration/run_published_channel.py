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
SCHEMAS_DIR = DAILY_PAPERS_DIR / "schemas"

for p in (SHARED_DIR, ADAPTERS_DIR, RANKING_DIR, SCHEMAS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from domain_ranker import provider_preference_multiplier, score_relevance
from metadata_ranker import compute_final_meta_score
from paper_fetcher_adapter import fetch_published_raw_records
from paper_records import LiteReviewPaperRecord, RawPaperRecord
from user_config import active_domain, active_domain_profile, published_channel_config


TMP_DIR = Path("/tmp")
RAW_PATH = TMP_DIR / "published_raw_200.json"
LITE_PATH = TMP_DIR / "published_lite_50.json"
PDF_CANDIDATES_PATH = TMP_DIR / "published_pdf_candidates_20.json"


def _safe_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _to_lite_record(raw: RawPaperRecord, pdf_candidate: bool) -> LiteReviewPaperRecord:
    decision = (
        "fetch_pdf"
        if pdf_candidate
        else ("hold" if raw.final_meta_score >= 0.45 else "skip")
    )
    confidence = min(1.0, max(0.1, raw.final_meta_score))
    reason = (
        "Strong metadata relevance and quality signal; worth getting full text."
        if decision == "fetch_pdf"
        else "Metadata suggests moderate value; queue behind higher-priority papers."
        if decision == "hold"
        else "Low metadata relevance or strong negative signal; skip for now."
    )

    return LiteReviewPaperRecord(
        **asdict(raw),
        review_tier="lite",
        evidence_scope="metadata_only",
        lite_decision=decision,
        lite_confidence=confidence,
        lite_reasoning=reason,
        recommended_for_pdf=pdf_candidate,
    )


def run() -> dict:
    config = published_channel_config()
    if not config.get("enabled", True):
        _safe_write_json(RAW_PATH, [])
        _safe_write_json(LITE_PATH, [])
        _safe_write_json(PDF_CANDIDATES_PATH, [])
        return {"status": "disabled"}

    domain_name = active_domain()
    profile = active_domain_profile()

    queries = profile.get("queries") or []
    if not queries:
        queries = ["intelligent construction"]
    query = queries[0]
    # Avoid exploding upstream API calls; keep a bounded alternate-query set.
    alternate_queries = queries[1:3]

    recall_n = int(config.get("recall_n", 200))
    lite_n = int(config.get("lite_n", 50))
    # Phase 2 output contract requires top20 PDF candidates file.
    pdf_candidate_n = 20

    raw_records, adapter_info = fetch_published_raw_records(
        query=query,
        alternate_queries=alternate_queries,
        recall_n=recall_n,
        providers=config.get("providers") or [],
        year_range=config.get("year_range", ""),
        has_abstract=config.get("has_abstract", True),
        journal_article_only=config.get("journal_article_only", False),
    )

    scored_records: list[RawPaperRecord] = []
    for record in raw_records:
        domain_match = score_relevance(
            title=record.title,
            abstract=record.abstract,
            domain_profile=profile,
        )

        if (
            len(domain_match.matched_negative_keywords) >= 2
            and domain_match.relevance_score <= 0.12
        ):
            # hard filter only for clearly off-domain papers; otherwise keep with penalty
            continue

        source_multiplier = provider_preference_multiplier(
            record.source_providers, profile
        )
        final_meta_score, components = compute_final_meta_score(
            record=asdict(record),
            relevance_score=domain_match.relevance_score,
            domain_multiplier=source_multiplier,
        )

        record.domain = domain_name
        record.matched_queries = domain_match.matched_queries
        record.matched_positive_keywords = domain_match.matched_positive_keywords
        record.matched_negative_keywords = domain_match.matched_negative_keywords
        record.matched_boost_keywords = domain_match.matched_boost_keywords
        record.relevance_score = components["relevance_score"]
        record.freshness_score = components["freshness_score"]
        record.provider_quality_score = components["provider_quality_score"]
        record.metadata_completeness_score = components["metadata_completeness_score"]
        record.publication_type_score = components["publication_type_score"]
        record.impact_score = components["impact_score"]
        record.accessibility_score = components["accessibility_score"]
        record.final_meta_score = final_meta_score
        record.metadata_trace.update(
            {
                "domain_multiplier": source_multiplier,
                "score_formula": "0.40*relevance + 0.15*freshness + 0.10*provider_quality + 0.10*metadata_completeness + 0.10*publication_type + 0.10*impact + 0.05*accessibility",
            }
        )
        scored_records.append(record)

    scored_records.sort(key=lambda r: r.final_meta_score, reverse=True)

    raw_top = scored_records[:recall_n]
    lite_top = raw_top[:lite_n]
    pdf_candidates = lite_top[:pdf_candidate_n]

    lite_records: list[LiteReviewPaperRecord] = []
    pdf_ids = {r.paper_id for r in pdf_candidates}
    for item in lite_top:
        lite_records.append(
            _to_lite_record(item, pdf_candidate=item.paper_id in pdf_ids)
        )

    _safe_write_json(RAW_PATH, [asdict(r) for r in raw_top])
    _safe_write_json(LITE_PATH, [asdict(r) for r in lite_records])
    _safe_write_json(
        PDF_CANDIDATES_PATH, [asdict(r) for r in lite_records if r.recommended_for_pdf]
    )

    return {
        "status": "ok",
        "adapter": adapter_info,
        "domain": domain_name,
        "query": query,
        "alternate_queries": alternate_queries,
        "counts": {
            "raw": len(raw_top),
            "lite": len(lite_records),
            "pdf_candidates": len(pdf_ids),
        },
        "outputs": {
            "published_raw_200": str(RAW_PATH),
            "published_lite_50": str(LITE_PATH),
            "published_pdf_candidates_20": str(PDF_CANDIDATES_PATH),
        },
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
