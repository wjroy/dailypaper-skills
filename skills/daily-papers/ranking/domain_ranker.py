#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DomainMatchResult:
    matched_queries: list[str]
    matched_positive_keywords: list[str]
    matched_negative_keywords: list[str]
    matched_boost_keywords: list[str]
    relevance_score: float


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _phrase_match_count(text: str, phrase: str) -> int:
    if not phrase:
        return 0
    escaped = re.escape(phrase)
    return len(re.findall(rf"\b{escaped}\b", text))


def _keyword_tokens(keyword: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", keyword.lower()) if len(t) > 1]


def _token_hit_count(text: str, keyword: str) -> int:
    tokens = _keyword_tokens(keyword)
    if not tokens:
        return 0
    return sum(1 for token in tokens if re.search(rf"\b{re.escape(token)}\b", text))


def score_relevance(
    title: str,
    abstract: str,
    domain_profile: dict,
) -> DomainMatchResult:
    title_n = _normalize(title)
    abstract_n = _normalize(abstract)
    full_text = f"{title_n} {abstract_n}".strip()

    queries = domain_profile.get("queries", []) or []
    positives = domain_profile.get("positive_keywords", []) or []
    negatives = domain_profile.get("negative_keywords", []) or []
    boosts = domain_profile.get("boost_keywords", []) or []

    matched_queries: list[str] = []
    matched_positives: list[str] = []
    matched_negatives: list[str] = []
    matched_boosts: list[str] = []

    score = 0.0

    # Exact phrase gets highest signal; title hit > abstract hit.
    for q in queries:
        qn = _normalize(q)
        if not qn:
            continue
        t_hits = _phrase_match_count(title_n, qn)
        a_hits = _phrase_match_count(abstract_n, qn)
        if t_hits or a_hits:
            matched_queries.append(q)
        score += 5.0 * t_hits + 2.0 * a_hits

    # Positive keywords: exact phrase first, then token-level soft match.
    for kw in positives:
        kwn = _normalize(kw)
        if not kwn:
            continue
        t_phrase = _phrase_match_count(title_n, kwn)
        a_phrase = _phrase_match_count(abstract_n, kwn)
        token_hits = _token_hit_count(full_text, kwn)
        if t_phrase or a_phrase or token_hits >= 2:
            matched_positives.append(kw)
        score += 3.0 * t_phrase + 1.2 * a_phrase + 0.3 * min(token_hits, 3)

    # Negative keywords: strong penalty (and can be filtered later).
    for kw in negatives:
        kwn = _normalize(kw)
        if not kwn:
            continue
        t_phrase = _phrase_match_count(title_n, kwn)
        a_phrase = _phrase_match_count(abstract_n, kwn)
        token_hits = _token_hit_count(full_text, kwn)
        if t_phrase or a_phrase or token_hits >= 2:
            matched_negatives.append(kw)
        score -= 8.0 * t_phrase + 5.0 * a_phrase + 0.8 * min(token_hits, 3)

    # Boost keywords: moderate positive signal.
    for kw in boosts:
        kwn = _normalize(kw)
        if not kwn:
            continue
        t_phrase = _phrase_match_count(title_n, kwn)
        a_phrase = _phrase_match_count(abstract_n, kwn)
        token_hits = _token_hit_count(full_text, kwn)
        if t_phrase or a_phrase or token_hits >= 2:
            matched_boosts.append(kw)
        score += 2.0 * t_phrase + 0.8 * a_phrase + 0.2 * min(token_hits, 2)

    # Normalize to [0, 1]. 6.0 baseline means one strong title phrase is meaningful.
    relevance_score = max(0.0, min(1.0, score / 6.0))

    return DomainMatchResult(
        matched_queries=matched_queries,
        matched_positive_keywords=matched_positives,
        matched_negative_keywords=matched_negatives,
        matched_boost_keywords=matched_boosts,
        relevance_score=relevance_score,
    )


def provider_preference_multiplier(
    source_providers: list[str], domain_profile: dict
) -> float:
    preferences = domain_profile.get("source_preferences", {}) or {}
    if not preferences or not source_providers:
        return 1.0

    weights = [float(preferences.get(provider, 1.0)) for provider in source_providers]
    if not weights:
        return 1.0
    return max(0.6, min(1.4, sum(weights) / len(weights)))
