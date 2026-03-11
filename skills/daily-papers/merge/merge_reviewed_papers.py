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

    payload = {
        "version": "merged-rich",
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
