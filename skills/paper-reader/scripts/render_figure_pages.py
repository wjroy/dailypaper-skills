#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from _figure_common import (
    command_exists,
    estimate_role,
    extract_caption_snippet,
    figures_dir_for_paper,
    page_keyword_hits,
    paper_id_from_inputs,
    pdftotext_pages,
    png_dimensions,
    read_json,
    run_command,
    slugify,
    write_json,
)


def should_trigger_fallback(
    embedded_records: list[dict], page_hits: dict[int, list[str]]
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    extracted_count = len(embedded_records)
    figure_like_pages = len(page_hits)
    role_counts = {"framework": 0, "method": 0, "result": 0}
    for record in embedded_records:
        role = record.get("estimated_role", "unknown")
        if role in role_counts:
            role_counts[role] += 1

    if extracted_count == 0:
        reasons.append("embedded extraction returned no usable figures")
    if figure_like_pages >= max(2, extracted_count + 1):
        reasons.append("text suggests figure-heavy pages beyond embedded results")
    if role_counts["framework"] + role_counts["method"] == 0:
        reasons.append("method or framework figures are still missing")
    if role_counts["result"] == 0:
        reasons.append("result figures are still missing")
    return (len(reasons) > 0, reasons)


def _render_with_pymupdf(
    pdf_path: Path, figures_dir: Path, pages_to_render: list[int], pages: list[str]
) -> tuple[list[dict], str]:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return [], str(exc)

    rendered_records: list[dict] = []
    try:
        with fitz.open(str(pdf_path)) as doc:
            for render_index, page_number in enumerate(pages_to_render, start=1):
                page_text = (
                    pages[page_number - 1] if page_number - 1 < len(pages) else ""
                )
                role = estimate_role(extract_caption_snippet(page_text), page_text)
                role_slug = slugify(role, default="unknown")
                filename = f"fig_{role_slug}_fullpage_p{page_number:02d}_{render_index:02d}.png"
                final_path = figures_dir / filename
                page = doc.load_page(page_number - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
                pix.save(str(final_path))
                width, height = png_dimensions(final_path)
                rendered_records.append(
                    {
                        "source_pdf": str(pdf_path),
                        "page_number": page_number,
                        "source_type": "rendered_fullpage",
                        "filename": filename,
                        "width": width,
                        "height": height,
                        "caption_snippet": extract_caption_snippet(page_text),
                        "estimated_role": role,
                        "include_in_key_figures": role
                        in {"framework", "method", "result"},
                        "extraction_confidence": "medium"
                        if role in {"framework", "method", "result"}
                        else "low",
                        "page_keyword_hits": page_keyword_hits(page_text),
                    }
                )
    except Exception as exc:
        return rendered_records, str(exc)
    return rendered_records, ""


def _render_with_pdftoppm(
    pdf_path: Path, figures_dir: Path, pages_to_render: list[int], pages: list[str]
) -> tuple[list[dict], str]:
    if not command_exists("pdftoppm"):
        return [], "pdftoppm is not available"
    rendered_records: list[dict] = []
    for render_index, page_number in enumerate(pages_to_render, start=1):
        page_text = pages[page_number - 1] if page_number - 1 < len(pages) else ""
        role = estimate_role(extract_caption_snippet(page_text), page_text)
        role_slug = slugify(role, default="unknown")
        prefix = figures_dir / f"render_page_{page_number:02d}"
        proc = run_command(
            [
                "pdftoppm",
                "-png",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(pdf_path),
                str(prefix),
            ]
        )
        if proc.returncode != 0:
            continue
        generated = sorted(figures_dir.glob(f"render_page_{page_number:02d}-*.png"))
        if not generated:
            continue
        raw_file = generated[0]
        filename = f"fig_{role_slug}_fullpage_p{page_number:02d}_{render_index:02d}.png"
        final_path = figures_dir / filename
        raw_file.replace(final_path)
        width, height = png_dimensions(final_path)
        rendered_records.append(
            {
                "source_pdf": str(pdf_path),
                "page_number": page_number,
                "source_type": "rendered_fullpage",
                "filename": filename,
                "width": width,
                "height": height,
                "caption_snippet": extract_caption_snippet(page_text),
                "estimated_role": role,
                "include_in_key_figures": role in {"framework", "method", "result"},
                "extraction_confidence": "medium"
                if role in {"framework", "method", "result"}
                else "low",
                "page_keyword_hits": page_keyword_hits(page_text),
            }
        )
    return rendered_records, ""


def render_pages(pdf_path: Path, paper_id: str) -> dict:
    figures_dir = figures_dir_for_paper(paper_id)
    figures_dir.mkdir(parents=True, exist_ok=True)
    embedded_payload = read_json(figures_dir / "embedded_figures.json", {"records": []})
    embedded_records = list(embedded_payload.get("records", []))

    pages = pdftotext_pages(pdf_path)
    page_hits = {
        index + 1: page_keyword_hits(text)
        for index, text in enumerate(pages)
        if page_keyword_hits(text)
    }
    should_render, reasons = should_trigger_fallback(embedded_records, page_hits)

    pages_to_render = sorted(page_hits)[:3] if should_render else []
    rendered_records, poppler_error = _render_with_pdftoppm(
        pdf_path, figures_dir, pages_to_render, pages
    )
    backend = "pdftoppm" if rendered_records else "none"
    message = poppler_error
    if not rendered_records and pages_to_render:
        rendered_records, pymupdf_error = _render_with_pymupdf(
            pdf_path, figures_dir, pages_to_render, pages
        )
        if rendered_records:
            backend = "pymupdf_page_snapshot"
            message = ""
        else:
            message = "; ".join(part for part in [poppler_error, pymupdf_error] if part)

    payload = {
        "status": "ok" if rendered_records or not should_render else "skipped",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "backend": backend,
        "rendered_count": len(rendered_records),
        "figure_like_pages": sorted(page_hits),
        "fallback_triggered": should_render,
        "fallback_reasons": reasons,
        "records": rendered_records,
        "message": message,
    }
    write_json(figures_dir / "rendered_pages.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()
    paper_id = paper_id_from_inputs(args.paper_id, pdf_path)
    payload = render_pages(pdf_path, paper_id)
    print(
        payload.get("message")
        or f"rendered fallback pages: {payload.get('rendered_count', 0)}"
    )


if __name__ == "__main__":
    main()
