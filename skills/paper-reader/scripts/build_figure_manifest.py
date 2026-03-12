#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from _figure_common import (
    confidence_label,
    estimate_role,
    extract_caption_snippet,
    figures_dir_for_paper,
    include_in_key_figures,
    manifest_path_for_paper,
    page_keyword_hits,
    paper_id_from_inputs,
    pdftotext_pages,
    png_dimensions,
    read_json,
    slugify,
    vault_relpath,
    write_json,
)


def enrich_record(
    record: dict, pages: list[str], figures_dir: Path, sequence: int
) -> dict:
    page_number = int(record.get("page_number", 0) or 0)
    page_text = pages[page_number - 1] if 0 < page_number <= len(pages) else ""
    caption_snippet = record.get("caption_snippet", "") or extract_caption_snippet(
        page_text
    )
    role = record.get("estimated_role", "unknown")
    if not role or role == "unknown":
        role = estimate_role(caption_snippet, page_text, record.get("filename", ""))

    filename = record.get("filename", "")
    figure_path = figures_dir / filename
    width = int(record.get("width", 0) or 0)
    height = int(record.get("height", 0) or 0)
    if figure_path.exists() and figure_path.suffix.lower() == ".png":
        width, height = png_dimensions(figure_path)

    source_type = record.get("source_type", "unknown")
    role_slug = slugify(role, default="unknown")
    if figure_path.exists() and figure_path.suffix.lower() == ".png":
        if source_type == "embedded":
            new_filename = f"fig_{role_slug}_p{page_number:02d}_{sequence:02d}.png"
        else:
            new_filename = (
                f"fig_{role_slug}_fullpage_p{page_number:02d}_{sequence:02d}.png"
            )
        new_path = figures_dir / new_filename
        if new_path != figure_path:
            figure_path.replace(new_path)
            figure_path = new_path
        filename = new_filename

    return {
        "source_pdf": record.get("source_pdf", ""),
        "page_number": page_number,
        "source_type": source_type,
        "filename": filename,
        "width": width,
        "height": height,
        "caption_snippet": caption_snippet,
        "estimated_role": role,
        "include_in_key_figures": include_in_key_figures(role),
        "extraction_confidence": confidence_label(source_type, role, caption_snippet),
        "vault_relpath": vault_relpath(figure_path) if figure_path.exists() else "",
        "page_keyword_hits": page_keyword_hits(page_text),
    }


def _recommended_figure_types() -> list[str]:
    return ["方法框架图", "主结果图"]


def _image_mode(records: list[dict], rendered_count: int) -> str:
    if not records:
        return "none"
    has_method = any(
        item.get("estimated_role") in {"framework", "method"} for item in records
    )
    has_result = any(item.get("estimated_role") == "result" for item in records)
    if has_method and has_result:
        return "full"
    return "partial"


def build_manifest(pdf_path: Path, paper_id: str) -> dict:
    figures_dir = figures_dir_for_paper(paper_id)
    embedded = read_json(figures_dir / "embedded_figures.json", {"records": []})
    rendered = read_json(figures_dir / "rendered_pages.json", {"records": []})
    pages = pdftotext_pages(pdf_path)

    all_records = []
    for index, record in enumerate(
        list(embedded.get("records", [])) + list(rendered.get("records", [])), start=1
    ):
        enriched = enrich_record(record, pages, figures_dir, index)
        if enriched["filename"]:
            all_records.append(enriched)

    method_framework_count = sum(
        1 for item in all_records if item["estimated_role"] in {"framework", "method"}
    )
    result_count = sum(1 for item in all_records if item["estimated_role"] == "result")
    rendered_count = len(rendered.get("records", []))
    manifest = {
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "figures_dir": str(figures_dir),
        "image_mode": _image_mode(all_records, rendered_count),
        "figures": all_records,
        "recommended_figure_types": _recommended_figure_types(),
        "stats": {
            "embedded_figures_extracted": len(embedded.get("records", [])),
            "rendered_fallback_pages": rendered_count,
            "total_candidate_figures": len(all_records),
            "key_method_framework_figures": method_framework_count,
            "key_result_figures": result_count,
            "figure_like_pages": len(rendered.get("figure_like_pages", [])),
        },
        "fallback": {
            "triggered": bool(rendered.get("fallback_triggered", False))
            or _image_mode(all_records, rendered_count) != "full",
            "reasons": list(rendered.get("fallback_reasons", [])),
        },
        "backends": {
            "embedded": embedded.get("backend", "none"),
            "rendered": rendered.get("backend", "none"),
        },
        "messages": [
            message
            for message in [embedded.get("message", ""), rendered.get("message", "")]
            if message
        ],
    }
    manifest_path = manifest_path_for_paper(paper_id)
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()
    paper_id = paper_id_from_inputs(args.paper_id, pdf_path)
    manifest = build_manifest(pdf_path, paper_id)
    print(
        f"figure manifest saved to: {manifest_path_for_paper(paper_id)} ({manifest['image_mode']})"
    )


if __name__ == "__main__":
    main()
