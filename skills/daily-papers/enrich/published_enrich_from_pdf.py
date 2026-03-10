#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def _run_pdftotext(pdf_path: Path, pages: int = 8, timeout: int = 60) -> str:
    cmd = ["pdftotext", "-f", "1", "-l", str(max(1, pages)), str(pdf_path), "-"]
    proc = subprocess.run(
        cmd, check=False, capture_output=True, text=True, timeout=timeout
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout or ""


def _extract_authors_heuristic(text: str) -> list[str]:
    # Heuristic: pick one line between title and abstract with comma-separated names.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    authors: list[str] = []
    for line in lines[:25]:
        if "abstract" in line.lower():
            break
        if (
            line.count(",") >= 1
            and 8 <= len(line) <= 220
            and not any(
                k in line.lower()
                for k in ["university", "institute", "department", "@"]
            )
        ):
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if 1 < len(parts) <= 12:
                cleaned = []
                for p in parts:
                    p = re.sub(r"\d+$", "", p).strip()
                    if 2 <= len(p) <= 60:
                        cleaned.append(p)
                if len(cleaned) >= 2:
                    authors = cleaned
                    break
    return authors


def _extract_affiliations_heuristic(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    inst_markers = [
        "university",
        "institute",
        "department",
        "laboratory",
        "school of",
        "college",
        "academy",
        "research center",
        "inc.",
        "corp",
        "ltd",
    ]
    for line in lines[:60]:
        low = line.lower()
        if any(m in low for m in inst_markers) and len(line) <= 220:
            out.append(re.sub(r"\s+", " ", line))
    return list(dict.fromkeys(out))[:12]


def _extract_section_headers(text: str) -> list[str]:
    headers = []
    pattern = re.compile(r"^\s*(\d+(?:\.\d+)*)?\s*([A-Z][A-Za-z0-9\-\s]{2,80})\s*$")
    candidates = {
        "introduction",
        "method",
        "methods",
        "approach",
        "experiments",
        "results",
        "discussion",
        "conclusion",
        "related work",
    }
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 90:
            continue
        m = pattern.match(line)
        if not m:
            continue
        h = m.group(2).strip()
        if h.lower() in candidates or (h.isupper() and len(h.split()) <= 8):
            headers.append(h.title() if h.isupper() else h)
    return list(dict.fromkeys(headers))[:20]


def _extract_captions(text: str, kind: str) -> list[str]:
    if kind == "figure":
        regex = re.compile(r"(?im)^\s*(figure|fig\.)\s*\d+[:\.]?\s*(.{8,220})$")
    else:
        regex = re.compile(r"(?im)^\s*table\s*\d+[:\.]?\s*(.{8,220})$")
    out = []
    for m in regex.finditer(text):
        cap = re.sub(r"\s+", " ", m.group(2)).strip()
        out.append(cap)
    return list(dict.fromkeys(out))[:12]


def _extract_method_names(text: str) -> list[str]:
    names = []
    patterns = [
        r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b",
        r"\b([A-Z]{2,}(?:-[0-9]+)?)\b",
    ]
    for pat in patterns:
        for m in re.findall(pat, text):
            if len(m) < 3:
                continue
            names.append(m)
    return list(dict.fromkeys(names))[:20]


def _extract_method_summary(text: str) -> str:
    # Metadata-safe heuristic from "method" section neighborhood.
    lines = text.splitlines()
    method_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"(?i)\b(method|approach|framework)\b", line):
            method_idx = i
            break
    if method_idx < 0:
        snippet = " ".join(lines[:30])
    else:
        snippet = " ".join(lines[method_idx : method_idx + 40])
    snippet = re.sub(r"\s+", " ", snippet).strip()
    return snippet[:700]


def _extract_experiment_clues(
    text: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    low = text.lower()
    exp = []
    real_world = []
    simulation = []
    baseline = []

    exp_markers = ["experiment", "dataset", "ablation", "benchmark", "evaluation"]
    real_markers = ["real-world", "field test", "on-site", "deployment", "real robot"]
    sim_markers = ["simulation", "simulator", "synthetic", "mujoco", "gazebo"]
    baseline_markers = ["baseline", "compared with", "state-of-the-art", "sota"]

    for m in exp_markers:
        if m in low:
            exp.append(m)
    for m in real_markers:
        if m in low:
            real_world.append(m)
    for m in sim_markers:
        if m in low:
            simulation.append(m)
    for m in baseline_markers:
        if m in low:
            baseline.append(m)

    return exp, real_world, simulation, baseline


def _confidence_from_text(text: str, fields_found: int, total_fields: int) -> float:
    if not text:
        return 0.05
    density = min(1.0, len(text) / 20000.0)
    completeness = fields_found / max(1, total_fields)
    return round(max(0.05, min(0.95, 0.35 * density + 0.65 * completeness)), 3)


def _load_pdf_map(pdf_map_path: Path | None) -> dict[str, list[str]]:
    if not pdf_map_path or not pdf_map_path.exists():
        return {}
    try:
        payload = json.loads(pdf_map_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping: dict[str, list[str]] = {}
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, str):
                mapping[str(k)] = [v]
            elif isinstance(v, list):
                mapping[str(k)] = [str(x) for x in v if str(x).strip()]
    elif isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("paper_id", "")).strip()
            pth = str(item.get("pdf_path", "")).strip()
            if pid and pth:
                mapping.setdefault(pid, []).append(pth)
    return mapping


def enrich_published_from_pdf(
    candidates: list[dict], pdf_map: dict[str, list[str]]
) -> list[dict]:
    out = []
    for item in candidates:
        enriched = dict(item)
        pid = str(item.get("paper_id", "")).strip()
        pdf_paths = [Path(p).expanduser() for p in pdf_map.get(pid, [])]
        existing = [p for p in pdf_paths if p.exists() and p.is_file()]

        missing_report: dict[str, str] = {}
        notes: list[str] = []

        if not existing:
            missing_report.update(
                {
                    "pdf": "No local PDF path provided/found for this paper_id",
                    "authors_affiliations": "PDF unavailable",
                    "section_headers": "PDF unavailable",
                    "captions": "PDF unavailable",
                    "method_summary": "PDF unavailable",
                    "experiment_clues": "PDF unavailable",
                }
            )
            enriched.update(
                {
                    "local_pdf_paths": [],
                    "section_headers": [],
                    "figure_captions": [],
                    "table_captions": [],
                    "method_summary": "",
                    "method_names": [],
                    "experiment_clues": [],
                    "real_world_clues": [],
                    "simulation_clues": [],
                    "baseline_candidates": [],
                    "extraction_confidence": 0.05,
                    "extraction_notes": ["Local PDF missing; no extraction attempted"],
                    "missing_field_report": missing_report,
                }
            )
            out.append(enriched)
            continue

        pdf_path = existing[0]
        text = _run_pdftotext(pdf_path)
        if not text.strip():
            missing_report.update(
                {
                    "pdf_text": "pdftotext returned empty output (possibly scanned PDF or parse failure)",
                    "method_summary": "Text extraction failed",
                }
            )
            notes.append("pdftotext failed or produced empty text")

        authors = _extract_authors_heuristic(text)
        affiliations = _extract_affiliations_heuristic(text)
        section_headers = _extract_section_headers(text)
        figure_captions = _extract_captions(text, kind="figure")
        table_captions = _extract_captions(text, kind="table")
        method_summary = _extract_method_summary(text)
        method_names = _extract_method_names(text)
        exp, real_world, simulation, baseline = _extract_experiment_clues(text)

        if not authors:
            missing_report["authors"] = (
                "Could not reliably parse author line from extracted text"
            )
        if not affiliations:
            missing_report["affiliations"] = "No affiliation-like lines detected"
        if not section_headers:
            missing_report["section_headers"] = (
                "Section headers not detected in extracted text"
            )
        if not figure_captions and not table_captions:
            missing_report["captions"] = "No figure/table caption patterns matched"
        if not method_summary:
            missing_report["method_summary"] = "Method/approach snippet not detected"

        found = sum(
            [
                bool(authors),
                bool(affiliations),
                bool(section_headers),
                bool(figure_captions or table_captions),
                bool(method_summary),
                bool(method_names),
                bool(exp or real_world or simulation),
                bool(baseline),
            ]
        )
        total = 8
        confidence = _confidence_from_text(text, found, total)

        enriched.update(
            {
                "authors": authors if authors else item.get("authors", []),
                "affiliations": affiliations
                if affiliations
                else item.get("affiliations", []),
                "local_pdf_paths": [str(pdf_path)],
                "section_headers": section_headers,
                "figure_captions": figure_captions,
                "table_captions": table_captions,
                "method_summary": method_summary,
                "method_names": method_names,
                "experiment_clues": exp,
                "real_world_clues": real_world,
                "simulation_clues": simulation,
                "baseline_candidates": baseline,
                "extraction_confidence": confidence,
                "extraction_notes": notes,
                "missing_field_report": missing_report,
            }
        )
        out.append(enriched)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich published candidates from local PDFs"
    )
    parser.add_argument(
        "--input",
        default="/tmp/published_pdf_candidates_20.json",
        help="Input candidate JSON path",
    )
    parser.add_argument(
        "--pdf-map",
        default="/tmp/published_pdf_inputs.json",
        help="JSON map for paper_id -> pdf_path(s)",
    )
    parser.add_argument(
        "--output",
        default="/tmp/published_enriched_20.json",
        help="Output enriched JSON path",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    pdf_map_path = Path(args.pdf_map)

    if not input_path.exists():
        output_path.write_text("[]\n", encoding="utf-8")
        return

    try:
        candidates = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception:
        candidates = []

    pdf_map = _load_pdf_map(pdf_map_path)
    enriched = enrich_published_from_pdf(candidates, pdf_map)
    output_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
