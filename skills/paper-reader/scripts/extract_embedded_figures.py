#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _figure_common import (
    command_exists,
    figures_dir_for_paper,
    paper_id_from_inputs,
    png_dimensions,
    run_command,
    slugify,
    write_json,
)


def parse_pdfimages_list(output: str) -> list[dict]:
    records: list[dict] = []
    for line in output.splitlines():
        if not re.match(r"^\s*\d+", line):
            continue
        parts = line.split()
        if len(parts) < 12:
            continue
        records.append(
            {
                "page_number": int(parts[0]),
                "image_index": int(parts[1]),
                "pdfimages_type": parts[2],
                "width": int(parts[3]),
                "height": int(parts[4]),
                "object_id": f"{parts[10]} {parts[11]}",
            }
        )
    return records


def _empty_payload(pdf_path: Path, paper_id: str, backend: str, message: str, status: str = "skipped") -> dict:
    return {
        "status": status,
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "backend": backend,
        "embedded_count": 0,
        "records": [],
        "message": message,
    }


def _extract_with_pymupdf(pdf_path: Path, paper_id: str) -> dict:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return _empty_payload(pdf_path, paper_id, "pymupdf", str(exc))

    figures_dir = figures_dir_for_paper(paper_id)
    figures_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    try:
        with fitz.open(str(pdf_path)) as doc:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                    xref = image_info[0]
                    extracted = doc.extract_image(xref)
                    image_bytes = extracted.get("image")
                    ext = extracted.get("ext", "png")
                    if not image_bytes:
                        continue
                    page_number = page_index + 1
                    filename = f"fig_{slugify('unknown', default='unknown')}_p{page_number:02d}_{len(records) + 1:02d}.{ext}"
                    final_path = figures_dir / filename
                    final_path.write_bytes(image_bytes)
                    width, height = png_dimensions(final_path) if final_path.suffix.lower() == ".png" else (0, 0)
                    records.append(
                        {
                            "source_pdf": str(pdf_path),
                            "page_number": page_number,
                            "source_type": "embedded",
                            "filename": filename,
                            "width": width,
                            "height": height,
                            "caption_snippet": "",
                            "estimated_role": "unknown",
                            "include_in_key_figures": False,
                            "extraction_confidence": "medium",
                            "object_id": str(xref),
                            "image_index": image_index,
                        }
                    )
    except Exception as exc:
        return _empty_payload(pdf_path, paper_id, "pymupdf", str(exc), status="error")

    payload = {
        "status": "ok",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "backend": "pymupdf",
        "embedded_count": len(records),
        "records": records,
        "message": "" if records else "No embedded raster images extracted via PyMuPDF",
    }
    write_json(figures_dir / "embedded_figures.json", payload)
    return payload


def _extract_with_pdfimages(pdf_path: Path, paper_id: str) -> dict:
    if not command_exists("pdfimages"):
        return _empty_payload(pdf_path, paper_id, "pdfimages", "pdfimages is not available")

    figures_dir = figures_dir_for_paper(paper_id)
    figures_dir.mkdir(parents=True, exist_ok=True)

    list_proc = run_command(["pdfimages", "-list", str(pdf_path)])
    if list_proc.returncode != 0:
        payload = _empty_payload(
            pdf_path,
            paper_id,
            "pdfimages",
            (list_proc.stderr or "pdfimages -list failed").strip(),
            status="error",
        )
        write_json(figures_dir / "embedded_figures.json", payload)
        return payload

    image_rows = parse_pdfimages_list(list_proc.stdout)
    prefix = figures_dir / "embedded_raw"
    extract_proc = run_command(["pdfimages", "-png", str(pdf_path), str(prefix)])
    if extract_proc.returncode != 0:
        payload = _empty_payload(
            pdf_path,
            paper_id,
            "pdfimages",
            (extract_proc.stderr or "pdfimages extraction failed").strip(),
            status="error",
        )
        write_json(figures_dir / "embedded_figures.json", payload)
        return payload

    extracted_files = sorted(figures_dir.glob("embedded_raw-*.png"))
    records: list[dict] = []
    for idx, raw_file in enumerate(extracted_files):
        meta = image_rows[idx] if idx < len(image_rows) else {}
        page_number = int(meta.get("page_number", 0) or 0)
        filename = f"fig_{slugify('unknown', default='unknown')}_p{page_number:02d}_{idx + 1:02d}.png"
        final_path = figures_dir / filename
        raw_file.replace(final_path)
        records.append(
            {
                "source_pdf": str(pdf_path),
                "page_number": page_number,
                "source_type": "embedded",
                "filename": filename,
                "width": int(meta.get("width", 0) or 0),
                "height": int(meta.get("height", 0) or 0),
                "caption_snippet": "",
                "estimated_role": "unknown",
                "include_in_key_figures": False,
                "extraction_confidence": "medium",
                "pdfimages_type": meta.get("pdfimages_type", ""),
                "object_id": meta.get("object_id", ""),
            }
        )

    payload = {
        "status": "ok",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "backend": "pdfimages",
        "embedded_count": len(records),
        "records": records,
        "message": "" if records else "No embedded raster images extracted via pdfimages",
    }
    write_json(figures_dir / "embedded_figures.json", payload)
    return payload


def extract_embedded(pdf_path: Path, paper_id: str) -> dict:
    payload = _extract_with_pymupdf(pdf_path, paper_id)
    if payload.get("status") == "ok" and payload.get("embedded_count", 0) > 0:
        return payload
    pdfimages_payload = _extract_with_pdfimages(pdf_path, paper_id)
    if pdfimages_payload.get("status") == "ok" or pdfimages_payload.get("embedded_count", 0) > 0:
        return pdfimages_payload

    figures_dir = figures_dir_for_paper(paper_id)
    figures_dir.mkdir(parents=True, exist_ok=True)
    message_parts = [item for item in [payload.get("message", ""), pdfimages_payload.get("message", "")] if item]
    final_payload = {
        "status": "skipped",
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "backend": "none",
        "embedded_count": 0,
        "records": [],
        "message": "; ".join(message_parts) or "No embedded image backend available",
    }
    write_json(figures_dir / "embedded_figures.json", final_payload)
    return final_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()
    paper_id = paper_id_from_inputs(args.paper_id, pdf_path)
    payload = extract_embedded(pdf_path, paper_id)
    print(payload["message"] or f"embedded figures extracted: {payload.get('embedded_count', 0)}")


if __name__ == "__main__":
    main()
