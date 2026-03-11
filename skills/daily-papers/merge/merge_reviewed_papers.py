#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


TMP_DIR = Path("/tmp")
PUBLISHED_RICH_PATH = TMP_DIR / "published_review_rich_20.json"
PREPRINT_RICH_PATH = TMP_DIR / "preprint_review_rich_20.json"
MERGED_PATH = TMP_DIR / "daily_review_merged.json"


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _decision_to_legacy_bucket(decision: str) -> str:
    mapping = {
        "must_read": "必读",
        "worth_reading": "值得看",
        "skip": "可跳过",
    }
    return mapping.get(decision, "值得看")


def _legacy_source_label(source: str) -> str:
    source = (source or "").lower()
    if source == "arxiv":
        return "arxiv"
    if source == "biorxiv":
        return "biorxiv"
    if source in {"semantic_scholar", "openalex", "crossref", "pubmed", "europe_pmc"}:
        return "published"
    return source or "unknown"


def _compat_record(item: dict) -> dict:
    # Compatibility fields for legacy notes/reader workflows.
    local_pdf_paths = list(item.get("local_pdf_paths", []))
    preferred_type = item.get("preferred_fulltext_input_type", "")
    preferred_value = item.get("preferred_fulltext_input_value", "")
    if not preferred_type or not preferred_value:
        if local_pdf_paths:
            preferred_type = "local_pdf"
            preferred_value = local_pdf_paths[0]
        elif item.get("pdf_url"):
            preferred_type = "pdf_url"
            preferred_value = item.get("pdf_url", "")
        elif item.get("source") == "arxiv":
            preferred_type = "arxiv_url"
            preferred_value = item.get("url", "")
        elif item.get("doi"):
            preferred_type = "doi_url"
            preferred_value = f"https://doi.org/{item.get('doi', '')}"
        else:
            preferred_type = "doi_url"
            preferred_value = item.get("url", "")

    return {
        "paper_id": item.get("paper_id", ""),
        "title": item.get("title", ""),
        "authors": item.get("authors", []),
        "affiliations": item.get("affiliations", []),
        "abstract": item.get("abstract", ""),
        "url": item.get("url", ""),
        "pdf": item.get("pdf_url", ""),
        "local_pdf_paths": local_pdf_paths,
        "zotero_attachment_paths": list(item.get("zotero_attachment_paths", []))
        or local_pdf_paths,
        "preferred_fulltext_input_type": preferred_type,
        "preferred_fulltext_input_value": preferred_value,
        "source": _legacy_source_label(item.get("source", "")),
        "score": float(item.get("final_meta_score", 0.0)),
        "method_names": item.get("method_names", []),
        "method_summary": item.get("method_summary", ""),
        "has_real_world": bool(item.get("real_world_clues")),
        "captions": (item.get("figure_captions", []) or [])
        + (item.get("table_captions", []) or []),
        "section_headers": item.get("section_headers", []),
        "decision": item.get("rich_decision", "worth_reading"),
        "decision_zh": _decision_to_legacy_bucket(
            item.get("rich_decision", "worth_reading")
        ),
        "rich_confidence": float(item.get("rich_confidence", 0.0)),
        "channel": item.get("channel", ""),
        "review_tier": item.get("review_tier", "rich"),
        "missing_field_report": item.get("missing_field_report", {}),
        "extraction_confidence": float(item.get("extraction_confidence", 0.0)),
        "inspiration_notes": item.get("inspiration_notes", ""),
    }


def merge_reviewed_papers() -> dict:
    published = _load_json(PUBLISHED_RICH_PATH)
    preprint = _load_json(PREPRINT_RICH_PATH)

    all_items = []
    for item in published + preprint:
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("source_channel", normalized.get("channel", ""))
            all_items.append(normalized)

    dedup: dict[str, dict] = {}
    for item in all_items:
        pid = (
            str(item.get("paper_id", "")).strip()
            or str(item.get("doi", "")).strip()
            or str(item.get("url", "")).strip()
        )
        if not pid:
            continue
        if pid not in dedup:
            dedup[pid] = item
            continue
        prev = dedup[pid]
        if float(item.get("rich_confidence", 0.0)) > float(
            prev.get("rich_confidence", 0.0)
        ):
            dedup[pid] = item

    merged_items = list(dedup.values())
    merged_items.sort(
        key=lambda x: (
            1 if x.get("rich_decision") == "must_read" else 0,
            1 if x.get("rich_decision") == "worth_reading" else 0,
            float(x.get("rich_confidence", 0.0)),
            float(x.get("final_meta_score", 0.0)),
        ),
        reverse=True,
    )

    compat_pool = [_compat_record(item) for item in merged_items]
    payload = {
        "version": "v2-merged-rich",
        "inputs": {
            "published_review_rich_20": str(PUBLISHED_RICH_PATH),
            "preprint_review_rich_20": str(PREPRINT_RICH_PATH),
        },
        "counts": {
            "published": len(published),
            "preprint": len(preprint),
            "merged": len(merged_items),
            "must_read": sum(
                1 for item in merged_items if item.get("rich_decision") == "must_read"
            ),
            "worth_reading": sum(
                1
                for item in merged_items
                if item.get("rich_decision") == "worth_reading"
            ),
            "skip": sum(
                1 for item in merged_items if item.get("rich_decision") == "skip"
            ),
        },
        "rich_reviewed_pool": merged_items,
        "legacy_compatible_pool": compat_pool,
        "notes_default_filter": {
            "rich_decision": "must_read",
            "decision_zh": "必读",
        },
    }

    MERGED_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = merge_reviewed_papers()
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(MERGED_PATH),
                "counts": payload.get("counts", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
