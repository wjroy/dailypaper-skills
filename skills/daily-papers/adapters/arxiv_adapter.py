#!/usr/bin/env python3

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from hashlib import sha1


ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _paper_id(arxiv_id: str, title: str) -> str:
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    key = sha1(title.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"arxiv:unknown:{key}"


def _fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "dailypaper-skills/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_arxiv_records(
    query: str,
    categories: list[str],
    max_results: int = 200,
    sort_by: str = "submittedDate",
) -> list[dict]:
    query_parts = []
    if categories:
        query_parts.append("(" + "+OR+".join(f"cat:{c}" for c in categories) + ")")
    if query.strip():
        query_parts.append(f"all:{urllib.parse.quote(query.strip())}")
    search_query = "+AND+".join(query_parts) if query_parts else "all:machine+learning"

    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={search_query}&sortBy={sort_by}&sortOrder=descending&max_results={max(1, min(2000, max_results))}"
    )

    try:
        xml_text = _fetch_url(url)
    except Exception:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    records: list[dict] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = " ".join(
            (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").split()
        )
        abstract = " ".join(
            (
                entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or ""
            ).split()
        )
        url_abs = (
            entry.findtext("atom:id", default="", namespaces=ATOM_NS) or ""
        ).strip()
        published = (
            entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
        )[:10]
        year = (
            int(published[:4])
            if len(published) >= 4 and published[:4].isdigit()
            else None
        )

        arxiv_id_match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url_abs)
        arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else ""

        authors = []
        affiliations = []
        for author in entry.findall("atom:author", ATOM_NS):
            name = (
                author.findtext("atom:name", default="", namespaces=ATOM_NS) or ""
            ).strip()
            if name:
                authors.append(name)
            for aff in author.findall("arxiv:affiliation", ATOM_NS):
                if aff.text and aff.text.strip():
                    affiliations.append(aff.text.strip())

        category = ""
        cat_node = entry.find("arxiv:primary_category", ATOM_NS)
        if cat_node is not None:
            category = cat_node.attrib.get("term", "")

        records.append(
            {
                "paper_id": _paper_id(arxiv_id, title),
                "channel": "preprint",
                "source": "arxiv",
                "source_providers": ["arxiv"],
                "source_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "affiliations": sorted(set(affiliations)),
                "doi": "",
                "url": url_abs,
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
                "venue": "arXiv",
                "publication_type": "preprint",
                "published_date": published,
                "year": year,
                "citation_count": 0,
                "is_open_access": True,
                "oa_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
                "oa_status": "green",
                "metadata_trace": {"category": category},
            }
        )

    return records
