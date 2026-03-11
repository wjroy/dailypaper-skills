#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
ORCH_DIR = DAILY_PAPERS_DIR / "orchestration"
MERGE_DIR = DAILY_PAPERS_DIR / "merge"
RENDER_DIR = DAILY_PAPERS_DIR / "render"
TMP_DIR = Path("/tmp")
PDF_INPUTS_PATH = TMP_DIR / "published_pdf_inputs.json"

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from pipeline_state import load_state, save_state, utc_now_iso


def _run(script_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(script_path)], check=False, capture_output=True, text=True
    )
    out = (proc.stdout or "").strip()
    try:
        payload: dict[str, Any] = json.loads(out) if out else {}
    except Exception:
        payload = {"raw_output": out}
    payload["returncode"] = proc.returncode
    return payload


def _run_renderer_final() -> dict[str, Any]:
    script = RENDER_DIR / "render_daily_recommendation.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--mode", "final"],
        check=False,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "").strip()
    try:
        payload: dict[str, Any] = json.loads(out) if out else {}
    except Exception:
        payload = {"raw_output": out}
    payload["returncode"] = proc.returncode
    return payload


def _count_available_local_pdfs(pdf_inputs_path: Path) -> int:
    if not pdf_inputs_path.exists():
        return 0
    try:
        payload = json.loads(pdf_inputs_path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    paths: list[str] = []
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, str):
                paths.append(value)
            elif isinstance(value, list):
                paths.extend([str(v) for v in value])
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("pdf_path"):
                paths.append(str(item["pdf_path"]))

    existing = 0
    for p in paths:
        path = Path(p).expanduser()
        if path.exists() and path.is_file():
            existing += 1
    return existing


def resume() -> dict[str, Any]:
    state = load_state()
    if state.get("stage") != "awaiting_published_pdf_import":
        return {
            "status": "error",
            "message": "pipeline_state is not awaiting_published_pdf_import",
            "state": state,
        }

    expected = int(state.get("expected_pdf_count", 20))
    available = _count_available_local_pdfs(PDF_INPUTS_PATH)
    auto_continue = bool(state.get("auto_continue_without_pdf", False))
    if available < expected and not auto_continue:
        return {
            "status": "waiting_for_more_pdfs",
            "message": "Not enough local PDFs to continue published rich stage.",
            "expected_pdf_count": expected,
            "available_pdf_count": available,
            "pdf_inputs_path": str(PDF_INPUTS_PATH),
            "hint": "Complete PDF download in Zotero and update /tmp/published_pdf_inputs.json, then run resume again.",
        }

    published_rich = _run(ORCH_DIR / "run_published_rich_channel.py")
    merged = _run(MERGE_DIR / "merge_reviewed_papers.py")
    recommendation_final = _run_renderer_final()

    finished_state = dict(state)
    finished_state.update(
        {
            "stage": "completed_after_resume",
            "resumed_at": utc_now_iso(),
            "available_pdf_count": available,
            "published_rich_completed": published_rich.get("returncode") == 0,
            "merge_completed": merged.get("returncode") == 0,
            "final_recommendation_rendered": recommendation_final.get("returncode")
            == 0,
            "next_step": "Proceed to notes generation stage (see skills/daily-papers/references/notes-stage-guide.md) for merged must-read papers.",
        }
    )
    save_state(finished_state)

    status = "ok"
    if (
        published_rich.get("returncode") != 0
        or merged.get("returncode") != 0
        or recommendation_final.get("returncode") != 0
    ):
        status = "partial"

    return {
        "status": status,
        "steps": {
            "published_rich": published_rich,
            "merge": merged,
            "recommendation_final": recommendation_final,
        },
        "state": finished_state,
        "outputs": {
            "published_enriched_20": "/tmp/published_enriched_20.json",
            "published_review_rich_20": "/tmp/published_review_rich_20.json",
            "daily_review_merged": "/tmp/daily_review_merged.json",
        },
    }


if __name__ == "__main__":
    print(json.dumps(resume(), ensure_ascii=False, indent=2))
