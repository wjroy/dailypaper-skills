#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


TMP_DIR = Path("/tmp")
DEFAULT_INPUT = TMP_DIR / "published_pdf_candidates_20.json"
RIS_PATH = TMP_DIR / "published_top20.ris"
BIB_PATH = TMP_DIR / "published_top20.bib"
DOI_PATH = TMP_DIR / "published_top20_doi.txt"


def _load_candidates(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _safe_key(text: str, idx: int) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", (text or "paper")).strip("_")
    if not base:
        base = "paper"
    return f"{base[:40]}_{idx}"


def _first_author_family(authors: list[str]) -> str:
    if not authors:
        return ""
    first = authors[0].strip()
    if not first:
        return ""
    parts = first.split()
    return parts[-1]


def _write_ris(candidates: list[dict]) -> None:
    lines: list[str] = []
    for item in candidates:
        lines.append("TY  - JOUR")
        title = item.get("title", "")
        if title:
            lines.append(f"TI  - {title}")
        for author in item.get("authors", []) or []:
            if author:
                lines.append(f"AU  - {author}")
        year = item.get("year")
        if year:
            lines.append(f"PY  - {year}")
        venue = item.get("venue", "")
        if venue:
            lines.append(f"JO  - {venue}")
        doi = item.get("doi", "")
        if doi:
            lines.append(f"DO  - {doi}")
        url = item.get("url", "") or item.get("pdf_url", "")
        if url:
            lines.append(f"UR  - {url}")
        abstract = (item.get("abstract", "") or "").replace("\n", " ").strip()
        if abstract:
            lines.append(f"AB  - {abstract}")
        lines.append("ER  - ")
        lines.append("")

    RIS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_bib(candidates: list[dict]) -> None:
    entries: list[str] = []
    for idx, item in enumerate(candidates, start=1):
        key = _safe_key(item.get("title", ""), idx)
        title = item.get("title", "")
        authors = " and ".join(item.get("authors", []) or [])
        year = item.get("year")
        venue = item.get("venue", "")
        doi = item.get("doi", "")
        url = item.get("url", "") or item.get("pdf_url", "")

        fields = []
        if title:
            fields.append(f"  title = {{{title}}}")
        if authors:
            fields.append(f"  author = {{{authors}}}")
        if year:
            fields.append(f"  year = {{{year}}}")
        if venue:
            fields.append(f"  journal = {{{venue}}}")
        if doi:
            fields.append(f"  doi = {{{doi}}}")
        if url:
            fields.append(f"  url = {{{url}}}")

        entry = "@article{" + key + ",\n" + ",\n".join(fields) + "\n}\n"
        entries.append(entry)

    BIB_PATH.write_text("\n".join(entries), encoding="utf-8")


def _write_doi(candidates: list[dict]) -> int:
    dois = []
    for item in candidates:
        doi = (item.get("doi", "") or "").strip()
        if doi:
            dois.append(doi)
    doi_unique = list(dict.fromkeys(dois))
    DOI_PATH.write_text(
        "\n".join(doi_unique) + ("\n" if doi_unique else ""), encoding="utf-8"
    )
    return len(doi_unique)


def export_zotero_bundle(input_path: Path = DEFAULT_INPUT) -> dict:
    candidates = _load_candidates(input_path)
    _write_ris(candidates)
    _write_bib(candidates)
    doi_count = _write_doi(candidates)
    return {
        "status": "ok",
        "input": str(input_path),
        "candidate_count": len(candidates),
        "doi_count": doi_count,
        "files": {
            "ris": str(RIS_PATH),
            "bib": str(BIB_PATH),
            "doi_txt": str(DOI_PATH),
        },
    }


def main() -> None:
    payload = export_zotero_bundle(DEFAULT_INPUT)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
