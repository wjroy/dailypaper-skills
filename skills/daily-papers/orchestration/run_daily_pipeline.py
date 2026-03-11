#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import argparse
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
MERGE_DIR = DAILY_PAPERS_DIR / "merge"
STATE_DIR = DAILY_PAPERS_DIR / "state"
SHARED_DIR = DAILY_PAPERS_DIR.parent / "_shared"
RENDER_DIR = DAILY_PAPERS_DIR / "render"
TMP_DIR = Path("/tmp")
PDF_INPUTS_PATH = TMP_DIR / "published_pdf_inputs.json"

for p in (STATE_DIR, SHARED_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline_state import load_state, save_state, utc_now_iso
from user_config import active_domain, published_channel_config


def _run(script_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(script_path)], check=False, capture_output=True, text=True
    )
    output = (proc.stdout or "").strip()
    try:
        payload: dict[str, Any] = json.loads(output) if output else {}
    except Exception:
        payload = {"raw_output": output}
    payload["returncode"] = proc.returncode
    return payload


def _run_renderer(mode: str) -> dict[str, Any]:
    script = RENDER_DIR / "render_daily_recommendation.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--mode", mode],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "").strip()
    try:
        payload: dict[str, Any] = json.loads(output) if output else {}
    except Exception:
        payload = {"raw_output": output}
    payload["returncode"] = proc.returncode
    return payload


def _has_pdf_inputs() -> bool:
    if not PDF_INPUTS_PATH.exists():
        return False
    try:
        payload = json.loads(PDF_INPUTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return False
    if isinstance(payload, dict):
        return any(isinstance(v, list) and len(v) > 0 for v in payload.values())
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            path = str(item.get("pdf_path", "")).strip()
            paths = item.get("local_pdf_paths", [])
            if path:
                return True
            if isinstance(paths, list) and any(str(p).strip() for p in paths):
                return True
    return False


def run() -> dict:
    state = load_state()
    if state.get("stage") == "awaiting_published_pdf_import":
        return {
            "status": "paused",
            "message": "Pipeline is waiting for manual PDF import in Zotero. Run resume command after PDFs are ready.",
            "state": state,
        }

    published_front = _run(CURRENT_DIR / "run_published_channel.py")
    preprint = _run(CURRENT_DIR / "run_preprint_channel.py")

    auto_continue = bool(
        published_channel_config().get("auto_continue_without_pdf", False)
    )
    pdf_inputs_ready = _has_pdf_inputs()
    if not auto_continue and not pdf_inputs_ready:
        zotero_files = (
            published_front.get("zotero_handoff", {}).get("files", {})
            if isinstance(published_front, dict)
            else {}
        )
        new_state = {
            "stage": "awaiting_published_pdf_import",
            "created_at": utc_now_iso(),
            "active_domain": active_domain(),
            "expected_pdf_count": int(published_channel_config().get("pdf_n", 20)),
            "auto_continue_without_pdf": auto_continue,
            "zotero_export_files": zotero_files,
            "published_pdf_candidates_path": "/tmp/published_pdf_candidates_20.json",
            "preprint_completed": preprint.get("returncode") == 0,
            "resume_command": "python skills/daily-papers/state/resume_published.py",
        }
        save_state(new_state)
        return {
            "status": "awaiting_published_pdf_import",
            "steps": {
                "published_front": published_front,
                "preprint": preprint,
                "recommendation_interim": _run_renderer("interim"),
            },
            "message": "Published channel paused for manual Zotero PDF retrieval. Import generated RIS/Bib/DOI files into Zotero, download PDFs, then run resume command.",
            "state": new_state,
            "outputs": {
                "published_raw_200": "/tmp/published_raw_200.json",
                "published_lite_50": "/tmp/published_lite_50.json",
                "published_pdf_candidates_20": "/tmp/published_pdf_candidates_20.json",
                "preprint_raw": "/tmp/preprint_raw.json",
                "preprint_enriched": "/tmp/preprint_enriched.json",
                "preprint_review_rich_20": "/tmp/preprint_review_rich_20.json",
            },
        }

    published_rich = _run(CURRENT_DIR / "run_published_rich_channel.py")
    merged = _run(MERGE_DIR / "merge_reviewed_papers.py")
    recommendation_final = _run_renderer("final")

    status = "ok"
    if any(
        step.get("returncode") != 0
        for step in [
            published_front,
            preprint,
            published_rich,
            merged,
            recommendation_final,
        ]
    ):
        status = "partial"

    notes: list[str] = []
    if auto_continue:
        notes.append(
            "auto_continue_without_pdf=true: Published rich may have low extraction confidence when local PDFs are missing."
        )
    elif pdf_inputs_ready:
        notes.append(
            "Detected /tmp/published_pdf_inputs.json with local PDF mappings; continued without pause."
        )

    return {
        "status": status,
        "steps": {
            "published_front": published_front,
            "preprint": preprint,
            "published_rich": published_rich,
            "merge": merged,
            "recommendation_final": recommendation_final,
        },
        "notes": notes,
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume-published",
        action="store_true",
        help="Resume published rich stage after manual PDF retrieval.",
    )
    args = parser.parse_args()

    if args.resume_published:
        result = _run(STATE_DIR / "resume_published.py")
    else:
        result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
