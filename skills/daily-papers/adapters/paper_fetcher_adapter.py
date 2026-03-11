#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from hashlib import sha1
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = CURRENT_DIR.parent / "schemas"
if str(SCHEMAS_DIR) not in sys.path:
    sys.path.insert(0, str(SCHEMAS_DIR))

from paper_records import RawPaperRecord


def _stable_id(source: str, source_id: str, title: str) -> str:
    key = f"{source}|{source_id}|{title}".encode("utf-8", errors="ignore")
    return f"{source}-{sha1(key).hexdigest()[:16]}"


def _paper_id_from_identifiers(
    doi: str, source: str, source_id: str, title: str
) -> str:
    if doi:
        return f"doi:{doi.lower()}"
    if source_id:
        return f"{source}:{source_id}"
    return _stable_id(source=source, source_id=source_id, title=title)


def _to_raw_record(item: Any, query: str) -> RawPaperRecord:
    item_dict = item.to_dict() if hasattr(item, "to_dict") else dict(item)
    source_providers = list(item_dict.get("source_providers") or [])
    primary_source = source_providers[0] if source_providers else "paper_fetcher"

    doi = (item_dict.get("doi") or "").strip()
    url = (item_dict.get("url") or "").strip()
    source_id = (
        item_dict.get("openalex_id") or item_dict.get("s2_paper_id") or doi or url or ""
    )

    return RawPaperRecord(
        paper_id=_paper_id_from_identifiers(
            doi=doi,
            source=primary_source,
            source_id=str(source_id),
            title=item_dict.get("title", ""),
        ),
        channel="published",
        source=primary_source,
        source_providers=source_providers,
        source_id=str(source_id),
        title=item_dict.get("title", "") or "",
        abstract=item_dict.get("abstract", "") or "",
        authors=list(item_dict.get("authors") or []),
        affiliations=[],
        doi=doi,
        url=url,
        pdf_url=item_dict.get("oa_url", "") or "",
        venue=item_dict.get("journal", "") or "",
        publication_type=item_dict.get("paper_type", "") or "",
        published_date="",
        year=item_dict.get("year"),
        citation_count=int(item_dict.get("citation_count") or 0),
        is_open_access=item_dict.get("is_oa"),
        oa_url=item_dict.get("oa_url", "") or "",
        oa_status=item_dict.get("oa_status", "") or "",
        metadata_trace={
            "source_query": item_dict.get("source_query", "") or query,
            "raw": item_dict,
        },
    )


def _load_search_aggregator() -> tuple[Any | None, str]:
    try:
        from paper_fetcher import Config, SearchAggregator

        return SearchAggregator(Config.load()), "import:paper_fetcher"
    except Exception:
        pass

    # Local path fallback for sibling repo layout.
    repo_root = CURRENT_DIR.parents[3]
    local_repo = repo_root / "paper-fetcher"
    if local_repo.exists():
        if str(local_repo) not in sys.path:
            sys.path.insert(0, str(local_repo))
        try:
            from paper_fetcher import Config, SearchAggregator

            return SearchAggregator(Config.load()), "import:local_repo"
        except Exception:
            pass

    return None, "none"


def _search_with_cli_fallback(
    query: str,
    alternate_queries: list[str],
    recall_n: int,
    providers: list[str],
    year_range: str,
    has_abstract: bool | None,
    journal_article_only: bool,
) -> list[dict[str, Any]]:
    cmd = [
        "paper-fetcher",
        "search",
        query,
        "--limit",
        str(max(1, recall_n)),
        "--json",
    ]
    for alt in alternate_queries:
        cmd.extend(["--alternate-query", alt])
    for provider in providers:
        cmd.extend(["--provider", provider])
    if year_range:
        cmd.extend(["--year", year_range])
    if has_abstract is True:
        cmd.append("--has-abstract")
    if has_abstract is False:
        cmd.append("--no-has-abstract")
    if journal_article_only:
        cmd.append("--journal-article-only")

    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            return []
        return json.loads(proc.stdout)
    except Exception:
        return []


def fetch_published_raw_records(
    query: str,
    alternate_queries: list[str],
    recall_n: int,
    providers: list[str],
    year_range: str = "",
    has_abstract: bool | None = True,
    journal_article_only: bool = False,
) -> tuple[list[RawPaperRecord], dict[str, Any]]:
    aggregator, mode = _load_search_aggregator()
    # Unpaywall in paper-fetcher performs per-record DOI lookups and can make
    # 200-recall runs unstable/slow; keep OA signals from OpenAlex/S2 in Phase 2.
    effective_providers = [
        p for p in providers if p not in {"unpaywall", "semantic_scholar"}
    ]
    if not effective_providers:
        effective_providers = providers

    if aggregator is not None:
        try:
            response = aggregator.search(
                query=query,
                alternate_queries=alternate_queries,
                page=1,
                page_size=max(1, recall_n),
                year_range=year_range,
                providers=effective_providers,
                has_abstract=has_abstract,
                journal_article_only=journal_article_only,
            )
            records = [_to_raw_record(item, query=query) for item in response.results]
            return records, {
                "adapter_mode": mode,
                "total_candidates": response.total_candidates,
                "effective_providers": effective_providers,
            }
        except Exception as exc:
            mode = f"{mode}:failed:{exc.__class__.__name__}"

    cli_records = _search_with_cli_fallback(
        query=query,
        alternate_queries=alternate_queries,
        recall_n=recall_n,
        providers=providers,
        year_range=year_range,
        has_abstract=has_abstract,
        journal_article_only=journal_article_only,
    )

    raw_records = [_to_raw_record(item, query=query) for item in cli_records]
    return raw_records, {
        "adapter_mode": f"{mode}|cli_fallback",
        "total_candidates": len(raw_records),
        "effective_providers": effective_providers,
    }


def raw_records_to_dicts(records: list[RawPaperRecord]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]
