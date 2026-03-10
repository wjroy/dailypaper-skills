#!/usr/bin/env python3

from __future__ import annotations

import re


METHOD_PATTERNS = [
    r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b",
    r"\b([A-Z]{2,}(?:-[0-9]+)?)\b",
]

REAL_WORLD_HINTS = [
    "field test",
    "real-world",
    "real robot",
    "deployment",
    "in situ",
    "on-site",
]

SIM_HINTS = [
    "simulation",
    "simulator",
    "synthetic dataset",
    "virtual environment",
    "gazebo",
    "mujoco",
]

BASELINE_HINTS = [
    "baseline",
    "compared with",
    "we compare",
    "state-of-the-art",
    "sota",
]


def _extract_methods(text: str) -> list[str]:
    out = []
    seen = set()
    for pattern in METHOD_PATTERNS:
        for m in re.findall(pattern, text):
            if len(m) < 3:
                continue
            key = m.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
    return out[:15]


def enrich_arxiv_preprint(record: dict) -> dict:
    title = record.get("title", "")
    abstract = record.get("abstract", "")
    text = f"{title} {abstract}".lower()

    real_world = [kw for kw in REAL_WORLD_HINTS if kw in text]
    simulation = [kw for kw in SIM_HINTS if kw in text]
    baseline = [kw for kw in BASELINE_HINTS if kw in text]
    methods = _extract_methods(f"{title} {abstract}")

    enriched = dict(record)
    enriched.update(
        {
            "section_headers": [],
            "figure_captions": [],
            "table_captions": [],
            "method_summary": abstract[:600] if abstract else "",
            "method_names": methods,
            "experiment_clues": [
                "metadata-only arXiv preprint enrich; no PDF parsing in this stage"
            ],
            "real_world_clues": real_world,
            "simulation_clues": simulation,
            "baseline_candidates": baseline,
            "extraction_confidence": 0.45 if abstract else 0.2,
            "extraction_notes": [
                "arXiv enrich in Phase 4 uses metadata/abstract heuristics; rich PDF extraction belongs to later stage"
            ],
            "missing_field_report": {
                "authors_affiliations": "not extracted from PDF/HTML in this preprint enrich stage",
                "captions": "missing because no PDF parse executed",
            },
        }
    )
    return enriched
