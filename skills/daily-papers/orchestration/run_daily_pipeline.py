#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
MERGE_DIR = DAILY_PAPERS_DIR / "merge"


def _run(script_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script_path)], check=False, capture_output=True, text=True
    )
    output = (proc.stdout or "").strip()
    try:
        payload = json.loads(output) if output else {}
    except Exception:
        payload = {"raw_output": output}
    payload["returncode"] = proc.returncode
    return payload


def run() -> dict:
    published_front = _run(CURRENT_DIR / "run_published_channel.py")
    preprint = _run(CURRENT_DIR / "run_preprint_channel.py")
    published_rich = _run(CURRENT_DIR / "run_published_rich_channel.py")
    merged = _run(MERGE_DIR / "merge_reviewed_papers.py")

    status = "ok"
    if any(
        step.get("returncode") != 0
        for step in [published_front, preprint, published_rich, merged]
    ):
        status = "partial"

    return {
        "status": status,
        "steps": {
            "published_front": published_front,
            "preprint": preprint,
            "published_rich": published_rich,
            "merge": merged,
        },
        "outputs": {
            "published_raw_200": "/tmp/published_raw_200.json",
            "published_lite_50": "/tmp/published_lite_50.json",
            "published_pdf_candidates_20": "/tmp/published_pdf_candidates_20.json",
            "published_enriched_20": "/tmp/published_enriched_20.json",
            "published_review_rich_20": "/tmp/published_review_rich_20.json",
            "preprint_raw": "/tmp/preprint_raw.json",
            "preprint_enriched": "/tmp/preprint_enriched.json",
            "preprint_review_rich_20": "/tmp/preprint_review_rich_20.json",
            "daily_review_merged": "/tmp/daily_review_merged.json",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
