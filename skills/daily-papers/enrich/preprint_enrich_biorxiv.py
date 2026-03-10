#!/usr/bin/env python3

from __future__ import annotations


BIO_METHOD_HINTS = [
    "single-cell",
    "rna-seq",
    "crisper",
    "western blot",
    "flow cytometry",
    "proteomics",
    "transcriptomics",
]

REAL_WORLD_HINTS = [
    "patient cohort",
    "clinical",
    "in vivo",
    "wet-lab",
    "animal model",
]

SIM_HINTS = [
    "in silico",
    "simulation",
    "synthetic",
]

BASELINE_HINTS = [
    "compared with",
    "benchmark",
    "baseline",
    "state-of-the-art",
]


def enrich_biorxiv_preprint(record: dict) -> dict:
    title = record.get("title", "")
    abstract = record.get("abstract", "")
    text = f"{title} {abstract}".lower()

    method_names = [kw for kw in BIO_METHOD_HINTS if kw in text]
    real_world = [kw for kw in REAL_WORLD_HINTS if kw in text]
    sim = [kw for kw in SIM_HINTS if kw in text]
    baseline = [kw for kw in BASELINE_HINTS if kw in text]

    enriched = dict(record)
    enriched.update(
        {
            "section_headers": [],
            "figure_captions": [],
            "table_captions": [],
            "method_summary": abstract[:600] if abstract else "",
            "method_names": method_names,
            "experiment_clues": [
                "bioRxiv enrich in Phase 4 uses abstract-level biological cue extraction"
            ],
            "real_world_clues": real_world,
            "simulation_clues": sim,
            "baseline_candidates": baseline,
            "extraction_confidence": 0.5 if abstract else 0.2,
            "extraction_notes": [
                "bioRxiv enrich does not reuse arXiv parser; uses biology-oriented keyword cues"
            ],
            "missing_field_report": {
                "affiliations": "not available in current bioRxiv details endpoint payload",
                "captions": "missing because no PDF parsing in this stage",
            },
        }
    )
    return enriched
