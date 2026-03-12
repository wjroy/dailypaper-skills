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
PAPER_READER_SCRIPT = (
    DAILY_PAPERS_DIR.parent / "paper-reader" / "scripts" / "run_paper_reader.py"
)
TMP_DIR = Path("/tmp")
PDF_INPUTS_PATH = TMP_DIR / "published_pdf_inputs.json"
PREPRINT_RICH_PATH = TMP_DIR / "preprint_review_rich_20.json"
MERGED_PATH = TMP_DIR / "daily_review_merged.json"

for p in (STATE_DIR, SHARED_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline_state import load_state, save_state, utc_now_iso, clear_state
from user_config import active_domain, published_channel_config


def _run(script_path: Path) -> dict[str, Any]:
    """Run a subprocess, never raising on failure."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
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
        if proc.returncode != 0 and proc.stderr:
            payload["stderr_summary"] = proc.stderr.strip()[:500]
        return payload
    except Exception as exc:
        return {"returncode": -1, "error": str(exc)}


def _run_args(command: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
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
        if proc.returncode != 0 and proc.stderr:
            payload["stderr_summary"] = proc.stderr.strip()[:500]
        return payload
    except Exception as exc:
        return {"returncode": -1, "error": str(exc)}


def _run_renderer(mode: str) -> dict[str, Any]:
    """Run the recommendation renderer, never raising on failure."""
    script = RENDER_DIR / "render_daily_recommendation.py"
    try:
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
    except Exception as exc:
        return {"returncode": -1, "error": str(exc)}


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


def _load_pdf_candidates_summary() -> list[dict]:
    """Load a brief summary of papers waiting for PDF, for user-facing output."""
    candidates_path = TMP_DIR / "published_pdf_candidates_20.json"
    if not candidates_path.exists():
        return []
    try:
        items = json.loads(candidates_path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        return [
            {
                "title": item.get("title", "(untitled)"),
                "doi": item.get("doi", ""),
                "url": item.get("url", ""),
            }
            for item in items[:20]
            if isinstance(item, dict)
        ]
    except Exception:
        return []


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return payload if isinstance(payload, type(default)) else default


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _note_link_from_path(note_path: str) -> str:
    stem = Path(note_path).stem.strip()
    return f"[[{stem}]]" if stem else ""


def _preferred_pdf_path(item: dict[str, Any]) -> str:
    paths = item.get("local_pdf_paths", []) or []
    if isinstance(paths, list):
        for value in paths:
            text = str(value or "").strip()
            if text:
                return text
    preferred_type = str(item.get("preferred_fulltext_input_type", "")).strip().lower()
    preferred_value = str(item.get("preferred_fulltext_input_value", "")).strip()
    if preferred_type == "local_pdf" and preferred_value:
        return preferred_value
    return ""


def _run_notes_stage(source_path: Path) -> dict[str, Any]:
    if source_path == MERGED_PATH:
        payload = _load_json(source_path, {})
        if not isinstance(payload, dict):
            return {"status": "skipped", "reason": "notes_source_missing", "items": []}
        items = payload.get("rich_reviewed_pool", [])
        container_key = "rich_reviewed_pool"
    else:
        payload = _load_json(source_path, [])
        items = payload
        container_key = ""

    if not isinstance(items, list):
        return {"status": "skipped", "reason": "notes_source_invalid", "items": []}

    note_results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("rich_decision", "")).lower() != "must_read":
            continue

        record_path = TMP_DIR / f"paper_reader_{item.get('paper_id', 'paper')}.json"
        _write_json(record_path, item)
        pdf_path = _preferred_pdf_path(item)
        command = [sys.executable, str(PAPER_READER_SCRIPT)]
        if pdf_path:
            command.append(pdf_path)
        command.extend(
            [
                "--record-json",
                str(record_path),
                "--paper-id",
                str(item.get("paper_id", "")),
            ]
        )

        reader = _run_args(command)
        note_status = "note_pending"
        if reader.get("returncode") == 0 and reader.get("note_path"):
            note_link = _note_link_from_path(str(reader.get("note_path", "")))
            if note_link:
                item["note_links"] = [note_link]
            image_mode = str(
                (reader.get("image") or {}).get("image_mode", "none")
            ).lower()
            item["note_status"] = "text_note" if image_mode == "none" else "ready"
            note_status = str(item.get("note_status"))
        else:
            item["note_links"] = []
            item["note_status"] = "note_pending"

        note_results.append(
            {
                "paper_id": item.get("paper_id", ""),
                "title": item.get("title", ""),
                "note_status": note_status,
                "note_links": item.get("note_links", []),
            }
        )

    if container_key:
        payload[container_key] = items
    else:
        payload = items
    _write_json(source_path, payload)

    ready = sum(1 for item in note_results if item["note_status"] == "ready")
    text_only = sum(1 for item in note_results if item["note_status"] == "text_note")
    pending = sum(1 for item in note_results if item["note_status"] == "note_pending")
    return {
        "status": "ok",
        "items": note_results,
        "counts": {
            "ready": ready,
            "text_only": text_only,
            "note_pending": pending,
        },
    }


def run() -> dict:
    state = load_state()

    # If previous run left a checkpoint AND PDF inputs are now available, auto-resume
    if state.get("stage") == "awaiting_published_pdf_import":
        if _has_pdf_inputs():
            # Auto-resume: PDFs are now available, continue the pipeline
            clear_state()
            # Fall through to normal pipeline execution
        else:
            # Still no PDFs. But instead of blocking, re-run the pipeline.
            # The logic below will handle the PDF absence gracefully by
            # producing an interim recommendation from available data.
            clear_state()

    # --- Run both channels independently ---
    published_front = _run(CURRENT_DIR / "run_published_channel.py")
    preprint = _run(CURRENT_DIR / "run_preprint_channel.py")

    published_front_ok = (
        isinstance(published_front, dict) and published_front.get("returncode") == 0
    )
    preprint_ok = isinstance(preprint, dict) and preprint.get("returncode") == 0

    # --- Determine whether Published rich review can proceed ---
    auto_continue = bool(
        published_channel_config().get("auto_continue_without_pdf", False)
    )
    pdf_inputs_ready = _has_pdf_inputs()
    published_needs_pdf = not auto_continue and not pdf_inputs_ready

    published_rich = {
        "returncode": -1,
        "skipped": True,
        "reason": "published_pdf_not_available",
    }
    if not published_needs_pdf and published_front_ok:
        published_rich = _run(CURRENT_DIR / "run_published_rich_channel.py")

    # --- Merge whatever is available ---
    merged = _run(MERGE_DIR / "merge_reviewed_papers.py")

    # --- Must-read notes stage (best effort) ---
    notes = _run_notes_stage(
        MERGED_PATH if MERGED_PATH.exists() else PREPRINT_RICH_PATH
    )

    # --- Render the best possible recommendation page ---
    if published_needs_pdf:
        # Render interim (preprint-only rich + published lite) as the primary output
        recommendation = _run_renderer("interim")
        render_mode = "interim"
    else:
        recommendation = _run_renderer("final")
        render_mode = "final"

    # --- Build user-facing result ---
    completed_steps = []
    skipped_steps = []
    failed_steps = []

    if preprint_ok:
        completed_steps.append("preprint_discovery")
    elif isinstance(preprint, dict) and preprint.get("returncode") != 0:
        failed_steps.append("preprint_discovery")

    if published_front_ok:
        completed_steps.append("published_discovery")
    elif isinstance(published_front, dict) and published_front.get("returncode") != 0:
        failed_steps.append("published_discovery")

    if published_needs_pdf:
        skipped_steps.append("published_deep_review")
    elif isinstance(published_rich, dict) and not published_rich.get("skipped"):
        if published_rich.get("returncode") == 0:
            completed_steps.append("published_deep_review")
        else:
            failed_steps.append("published_deep_review")

    if isinstance(merged, dict) and merged.get("returncode") == 0:
        completed_steps.append("merge")
    elif isinstance(merged, dict) and merged.get("returncode") != 0:
        failed_steps.append("merge")

    if isinstance(recommendation, dict) and recommendation.get("returncode") == 0:
        completed_steps.append("recommendation_page")

    if isinstance(notes, dict) and notes.get("status") == "ok":
        completed_steps.append("must_read_notes")

    # Determine overall status
    if not completed_steps:
        status = "failed"
    elif failed_steps or skipped_steps:
        status = "partial"
    else:
        status = "ok"

    # Build the pending_pdfs list only when relevant
    pending_pdfs = []
    if published_needs_pdf:
        pending_pdfs = _load_pdf_candidates_summary()
        # Save state for potential auto-resume on next run
        new_state = {
            "stage": "awaiting_published_pdf_import",
            "created_at": utc_now_iso(),
            "active_domain": active_domain(),
            "expected_pdf_count": int(published_channel_config().get("pdf_n", 20)),
            "auto_continue_without_pdf": auto_continue,
            "preprint_completed": preprint_ok,
        }
        save_state(new_state)

    notes_summary: list[str] = []
    if auto_continue and not pdf_inputs_ready:
        notes_summary.append(
            "Published deep review ran without local PDFs; extraction confidence may be lower."
        )
    if published_needs_pdf and preprint_ok:
        notes_summary.append(
            "Published papers without local PDFs are marked as PDF pending. Add the PDFs and rerun daily-papers to continue."
        )
    if isinstance(notes, dict) and notes.get("counts"):
        counts = notes["counts"]
        notes_summary.append(
            "Must-read notes: "
            f"{counts.get('ready', 0)} enhanced, "
            f"{counts.get('text_only', 0)} text-only, "
            f"{counts.get('note_pending', 0)} note pending."
        )

    result: dict[str, Any] = {
        "status": status,
        "render_mode": render_mode,
        "completed_steps": completed_steps,
        "skipped_steps": skipped_steps,
        "failed_steps": failed_steps,
        "notes": notes_summary,
        "recommendation_output": recommendation.get("output", ""),
        "recommendation_counts": recommendation.get("counts", {}),
        "must_read_notes": notes.get("counts", {}),
    }

    if pending_pdfs:
        result["pending_published_pdfs"] = pending_pdfs
        result["pending_pdf_action"] = (
            "Add these PDFs to your local library, then rerun the daily recommendation."
        )

    # Internal debug info (for logging, not user-facing)
    result["_internal"] = {
        "published_front": published_front,
        "preprint": preprint,
        "published_rich": published_rich,
        "merge": merged,
        "notes": notes,
        "recommendation": recommendation,
    }

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
