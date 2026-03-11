#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _figure_common import (
    figures_dir_for_paper,
    paper_id_from_inputs,
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
                "color": parts[5],
                "components": int(parts[6]),
                "bits_per_component": int(parts[7]),
                "encoding": parts[8],
                "interpolate": parts[9],
                "object_id": f"{parts[10]} {parts[11]}",
            }
        )
    return records


def extract_embedded(pdf_path: Path, paper_id: str) -> dict:
    figures_dir = figures_dir_for_paper(paper_id)
    figures_dir.mkdir(parents=True, exist_ok=True)

    list_proc = run_command(["pdfimages", "-list", str(pdf_path)])
    if list_proc.returncode != 0:
        return {
            "status": "error",
            "paper_id": paper_id,
            "pdf_path": str(pdf_path),
            "records": [],
            "message": (list_proc.stderr or "pdfimages -list failed").strip(),
        }

    image_rows = parse_pdfimages_list(list_proc.stdout)
    prefix = figures_dir / "embedded_raw"
    extract_proc = run_command(["pdfimages", "-png", str(pdf_path), str(prefix)])
    if extract_proc.returncode != 0:
        return {
            "status": "error",
            "paper_id": paper_id,
            "pdf_path": str(pdf_path),
            "records": [],
            "message": (extract_proc.stderr or "pdfimages extraction failed").strip(),
        }

    extracted_files = sorted(figures_dir.glob("embedded_raw-*.png"))
    records: list[dict] = []
    for idx, raw_file in enumerate(extracted_files):
        meta = image_rows[idx] if idx < len(image_rows) else {}
        page_number = int(meta.get("page_number", 0) or 0)
        role_hint = "unknown"
        filename = f"fig_{slugify(role_hint, default='unknown')}_p{page_number:02d}_{idx + 1:02d}.png"
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
        "embedded_count": len(records),
        "records": records,
    }
    write_json(figures_dir / "embedded_figures.json", payload)
    print(f"embedded figures extracted: {len(records)}")
    print(f"embedded figure metadata saved to: {figures_dir / 'embedded_figures.json'}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()
    paper_id = paper_id_from_inputs(args.paper_id, pdf_path)
    extract_embedded(pdf_path, paper_id)


if __name__ == "__main__":
    main()
