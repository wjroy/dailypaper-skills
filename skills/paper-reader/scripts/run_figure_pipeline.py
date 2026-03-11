#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_figure_manifest import build_manifest
from extract_embedded_figures import extract_embedded
from link_figures_to_note import link_figures
from render_figure_pages import render_pages
from _figure_common import manifest_path_for_paper, paper_id_from_inputs


def run_pipeline(pdf_path: Path, paper_id: str, note_path: Path | None = None) -> dict:
    embedded = extract_embedded(pdf_path, paper_id)
    rendered = render_pages(pdf_path, paper_id)
    manifest = build_manifest(pdf_path, paper_id)

    linked = False
    manifest_path = manifest_path_for_paper(paper_id)
    if note_path is not None and note_path.exists():
        linked = link_figures(note_path, manifest_path)

    return {
        "status": "ok",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "manifest_path": str(manifest_path),
        "embedded_figures_extracted": embedded.get("embedded_count", 0),
        "rendered_fallback_pages": rendered.get("rendered_count", 0),
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
