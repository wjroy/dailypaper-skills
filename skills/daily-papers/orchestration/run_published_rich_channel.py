#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
SHARED_DIR = DAILY_PAPERS_DIR.parent / "_shared"
ENRICH_DIR = DAILY_PAPERS_DIR / "enrich"
SCHEMAS_DIR = DAILY_PAPERS_DIR / "schemas"

for p in (SHARED_DIR, ENRICH_DIR, SCHEMAS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from paper_records import RichReviewPaperRecord
from user_config import published_channel_config


TMP_DIR = Path("/tmp")
PDF_CANDIDATES_PATH = TMP_DIR / "published_pdf_candidates_20.json"
PDF_MAP_PATH = TMP_DIR / "published_pdf_inputs.json"
ENRICHED_PATH = TMP_DIR / "published_enriched_20.json"
REVIEW_RICH_PATH = TMP_DIR / "published_review_rich_20.json"


def _safe_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _run_enrich_from_pdf() -> bool:
    script = ENRICH_DIR / "published_enrich_from_pdf.py"
    cmd = [
        sys.executable,
        str(script),
        "--input",
        str(PDF_CANDIDATES_PATH),
        "--pdf-map",
        str(PDF_MAP_PATH),
        "--output",
        str(ENRICHED_PATH),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return proc.returncode == 0


def _make_rich_record(item: dict) -> RichReviewPaperRecord:
    meta = float(item.get("final_meta_score", 0.0))
    ext = float(item.get("extraction_confidence", 0.0))
    composite = 0.7 * meta + 0.3 * ext

    if composite >= 0.72:
        decision = "must_read"
    elif composite >= 0.5:
        decision = "worth_reading"
    else:
        decision = "skip"

    if item.get("missing_field_report"):
        caveat = "Some rich fields are missing; verify with manual reading before hard claims."
    else:
        caveat = "Enriched from local PDF text; still validate nuanced claims manually."

    return RichReviewPaperRecord(
        paper_id=item.get("paper_id", ""),
        channel="published",
        source=item.get("source", ""),
        source_providers=list(item.get("source_providers", [])),
        source_id=item.get("source_id", ""),
        title=item.get("title", ""),
        abstract=item.get("abstract", ""),
        authors=list(item.get("authors", [])),
        affiliations=list(item.get("affiliations", [])),
        doi=item.get("doi", ""),
        url=item.get("url", ""),
        pdf_url=item.get("pdf_url", ""),
        venue=item.get("venue", ""),
        publication_type=item.get("publication_type", ""),
        published_date=item.get("published_date", ""),
        year=item.get("year"),
        citation_count=int(item.get("citation_count", 0)),
        is_open_access=item.get("is_open_access"),
        oa_url=item.get("oa_url", ""),
        oa_status=item.get("oa_status", ""),
        domain=item.get("domain", ""),
        matched_queries=list(item.get("matched_queries", [])),
        matched_positive_keywords=list(item.get("matched_positive_keywords", [])),
        matched_negative_keywords=list(item.get("matched_negative_keywords", [])),
        matched_boost_keywords=list(item.get("matched_boost_keywords", [])),
        provider_quality_score=float(item.get("provider_quality_score", 0.0)),
        metadata_completeness_score=float(item.get("metadata_completeness_score", 0.0)),
        relevance_score=float(item.get("relevance_score", 0.0)),
        freshness_score=float(item.get("freshness_score", 0.0)),
        publication_type_score=float(item.get("publication_type_score", 0.0)),
        impact_score=float(item.get("impact_score", 0.0)),
        accessibility_score=float(item.get("accessibility_score", 0.0)),
        final_meta_score=float(item.get("final_meta_score", 0.0)),
        metadata_trace=item.get("metadata_trace", {}),
        review_tier="rich",
        evidence_scope="enriched_metadata_or_pdf",
        lite_decision=item.get("lite_decision", "hold"),
        lite_confidence=float(item.get("lite_confidence", max(0.2, meta))),
        lite_reasoning=item.get("lite_reasoning", ""),
        recommended_for_pdf=bool(item.get("recommended_for_pdf", False)),
        local_pdf_paths=list(item.get("local_pdf_paths", [])),
        section_headers=list(item.get("section_headers", [])),
        figure_captions=list(item.get("figure_captions", [])),
        table_captions=list(item.get("table_captions", [])),
        method_summary=item.get("method_summary", ""),
        method_names=list(item.get("method_names", [])),
        experiment_clues=list(item.get("experiment_clues", [])),
        real_world_clues=list(item.get("real_world_clues", [])),
        simulation_clues=list(item.get("simulation_clues", [])),
        baseline_candidates=list(item.get("baseline_candidates", [])),
        extraction_confidence=float(item.get("extraction_confidence", 0.0)),
        extraction_notes=list(item.get("extraction_notes", [])),
        missing_field_report=dict(item.get("missing_field_report", {})),
        rich_decision=decision,
        rich_confidence=max(0.2, min(1.0, composite)),
        core_method=(item.get("method_summary", "") or "")[:320],
        compared_methods=list(item.get("baseline_candidates", [])),
        borrowing_value=caveat,
        sharp_commentary="Published rich review auto-generated from local PDF enrich + metadata signals.",
        note_links=[],
    )


def run() -> dict:
    cfg = published_channel_config()
    if not cfg.get("enabled", True):
        _safe_write_json(ENRICHED_PATH, [])
        _safe_write_json(REVIEW_RICH_PATH, [])
        return {"status": "disabled"}

    _run_enrich_from_pdf()
    if not ENRICHED_PATH.exists():
        _safe_write_json(ENRICHED_PATH, [])

    try:
        enriched = json.loads(ENRICHED_PATH.read_text(encoding="utf-8"))
    except Exception:
        enriched = []

    rich_n = int(cfg.get("rich_n", 20))
    enriched = sorted(
        enriched, key=lambda x: float(x.get("final_meta_score", 0.0)), reverse=True
    )
    selected = enriched[: max(1, rich_n)]

    rich_records = [_make_rich_record(item) for item in selected]
    _safe_write_json(REVIEW_RICH_PATH, [asdict(r) for r in rich_records])

    return {
        "status": "ok",
        "counts": {
            "enriched": len(enriched),
            "review_rich": len(rich_records),
        },
        "outputs": {
            "published_enriched_20": str(ENRICHED_PATH),
            "published_review_rich_20": str(REVIEW_RICH_PATH),
        },
        "notes": [
            "If /tmp/published_pdf_inputs.json is missing or incomplete, extraction confidence stays low and missing fields are explicitly reported."
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
