#!/usr/bin/env python3

from __future__ import annotations

import json
import urllib.request
from datetime import date, timedelta
from hashlib import sha1


def _fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "dailypaper-skills/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _paper_id(doi: str, title: str) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    key = sha1(title.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"biorxiv:unknown:{key}"


def fetch_biorxiv_records(
    query: str,
    server: str = "biorxiv",
    max_results: int = 200,
    window_days: int = 30,
) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=max(1, window_days))
    # bioRxiv API does not support full-text query in this endpoint; we fetch recent
    # window then domain-rank downstream.
    url = f"https://api.biorxiv.org/details/{server}/{start.isoformat()}/{end.isoformat()}/0"

    try:
        payload = _fetch_json(url)
    except Exception:
        return []

    collection = payload.get("collection", []) or []
    records: list[dict] = []
    q_lower = (query or "").lower()
    for item in collection:
        title = (item.get("title") or "").strip()
        abstract = (item.get("abstract") or "").strip()
        text = f"{title} {abstract}".lower()
        if q_lower and q_lower not in text:
            # keep loose filtering; ranking does main relevance screening
            pass

        doi = (item.get("doi") or "").strip()
        authors_raw = (item.get("authors") or "").strip()
        authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
        published = (item.get("date") or "").strip()
        year = (
            int(published[:4])
            if len(published) >= 4 and published[:4].isdigit()
            else None
        )
        abs_url = f"https://www.biorxiv.org/content/{doi}v1" if doi else ""
        pdf_url = f"https://www.biorxiv.org/content/{doi}v1.full.pdf" if doi else ""

        records.append(
            {
                "paper_id": _paper_id(doi, title),
                "channel": "preprint",
                "source": "biorxiv",
                "source_providers": ["biorxiv"],
                "source_id": doi,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "affiliations": [],
                "doi": doi,
                "url": abs_url,
                "pdf_url": pdf_url,
                "venue": "bioRxiv",
                "publication_type": "preprint",
                "published_date": published,
                "year": year,
                "citation_count": 0,
                "is_open_access": True,
                "oa_url": pdf_url,
                "oa_status": "green",
                "metadata_trace": {
                    "server": server,
                    "version": item.get("version", ""),
                },
            }
        )

    return records[: max(1, max_results)]
