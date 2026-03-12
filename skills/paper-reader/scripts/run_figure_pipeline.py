#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _figure_common import manifest_path_for_paper, paper_id_from_inputs, write_json
from build_figure_manifest import build_manifest
from extract_embedded_figures import extract_embedded
from link_figures_to_note import link_figures
from render_figure_pages import render_pages


def _safe_call(func, *args):
    try:
        return func(*args)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "records": []}


def run_pipeline(pdf_path: Path, paper_id: str, note_path: Path | None = None) -> dict:
    embedded = _safe_call(extract_embedded, pdf_path, paper_id)
    rendered = _safe_call(render_pages, pdf_path, paper_id)
    manifest = _safe_call(build_manifest, pdf_path, paper_id)

    if "paper_id" not in manifest:
        manifest = {
            "paper_id": paper_id,
            "pdf_path": str(pdf_path),
            "image_mode": "none",
            "figures": [],
            "recommended_figure_types": ["方法框架图", "主结果图"],
            "stats": {
                "embedded_figures_extracted": 0,
                "rendered_fallback_pages": 0,
                "total_candidate_figures": 0,
                "key_method_framework_figures": 0,
                "key_result_figures": 0,
                "figure_like_pages": 0,
            },
            "fallback": {"triggered": False, "reasons": []},
            "backends": {"embedded": "none", "rendered": "none"},
            "messages": [
                item
                for item in [
                    embedded.get("message", ""),
                    rendered.get("message", ""),
                    manifest.get("message", ""),
                ]
                if item
            ],
        }
        write_json(manifest_path_for_paper(paper_id), manifest)

    linked = False
    manifest_path = manifest_path_for_paper(paper_id)
    if note_path is not None and note_path.exists():
        linked_result = _safe_call(link_figures, note_path, manifest_path)
        linked = linked_result if isinstance(linked_result, bool) else False

    return {
        "status": "ok",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "manifest_path": str(manifest_path),
        "image_mode": manifest.get("image_mode", "none"),
        "embedded_figures_extracted": manifest.get("stats", {}).get(
            "embedded_figures_extracted", 0
        ),
        "rendered_fallback_pages": manifest.get("stats", {}).get(
            "rendered_fallback_pages", 0
        ),
        "total_candidate_figures": manifest.get("stats", {}).get(
            "total_candidate_figures", 0
        ),
        "key_method_framework_figures": manifest.get("stats", {}).get(
            "key_method_framework_figures", 0
        ),
        "key_result_figures": manifest.get("stats", {}).get("key_result_figures", 0),
        "fallback_triggered": manifest.get("fallback", {}).get("triggered", False),
        "fallback_reasons": manifest.get("fallback", {}).get("reasons", []),
        "note_linked_with_figures": linked,
        "messages": manifest.get("messages", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--paper-id", default="")
    parser.add_argument("--note-path", default="")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    paper_id = paper_id_from_inputs(args.paper_id, pdf_path)
    note_path = Path(args.note_path).expanduser().resolve() if args.note_path else None
    payload = run_pipeline(pdf_path, paper_id, note_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
