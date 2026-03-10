#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path


DEFAULT_CONFIG = {
    "paths": {
        "obsidian_vault": "~/ObsidianVault",
        "paper_notes_folder": "论文笔记",
        "daily_papers_folder": "DailyPapers",
        "concepts_folder": "_概念",
        "zotero_db": "~/Zotero/zotero.sqlite",
        "zotero_storage": "~/Zotero/storage",
    },
    "active_domain": "intelligent_construction",
    "published_channel": {
        "enabled": True,
        "backend": "paper_fetcher",
        "recall_n": 200,
        "lite_n": 50,
        "pdf_n": 50,
        "rich_n": 20,
        "providers": [
            "semantic_scholar",
            "openalex",
            "crossref",
            "pubmed",
            "europe_pmc",
            "unpaywall",
        ],
        "year_range": "",
        "journal_article_only": False,
        "has_abstract": True,
    },
    "preprint_channel": {
        "enabled": True,
        "source_mode": "adaptive",
        "default_source": "arxiv",
        "rich_n": 20,
        "sources": {
            "arxiv": {
                "enabled": True,
                "categories": ["cs.RO", "cs.CV", "cs.AI", "cs.LG"],
                "max_results": 200,
                "sort_by": "submittedDate",
            },
            "biorxiv": {
                "enabled": True,
                "max_results": 200,
                "window_days": 30,
                "server": "biorxiv",
            },
        },
    },
    "domain_profiles": {
        "intelligent_construction": {
            "queries": [
                "intelligent construction",
                "construction robotics",
                "geotechnical monitoring",
                "foundation pit",
                "embodied ai for civil engineering",
            ],
            "positive_keywords": [
                "construction",
                "geotechnical",
                "foundation pit",
                "embodied ai",
                "robotics",
                "autonomous excavation",
                "digital twin",
            ],
            "negative_keywords": [
                "medical imaging",
                "weather forecast",
                "protein design",
                "drug discovery",
                "speech synthesis",
                "gui agent",
                "text-to-sql",
            ],
            "boost_keywords": [
                "field deployment",
                "real-world",
                "earthwork",
                "tunnel",
                "safety monitoring",
                "sim-to-real",
            ],
            "source_preferences": {
                "semantic_scholar": 1.0,
                "openalex": 1.0,
                "crossref": 1.0,
                "pubmed": 0.2,
                "europe_pmc": 0.2,
                "arxiv": 1.0,
                "biorxiv": 0.1,
            },
            "preprint_source": "arxiv",
        },
        "biology": {
            "queries": [
                "immunology",
                "molecular biology",
                "bioinformatics",
                "single-cell sequencing",
                "protein interaction",
            ],
            "positive_keywords": [
                "immunology",
                "molecular biology",
                "bioinformatics",
                "single-cell",
                "transcriptomics",
                "proteomics",
                "gene regulation",
            ],
            "negative_keywords": [
                "autonomous driving",
                "robot manipulation",
                "construction machinery",
                "computer graphics",
                "game engine",
            ],
            "boost_keywords": [
                "in vivo",
                "clinical cohort",
                "wet-lab validation",
                "benchmark dataset",
                "causal mechanism",
            ],
            "source_preferences": {
                "semantic_scholar": 1.0,
                "openalex": 1.0,
                "crossref": 0.9,
                "pubmed": 1.2,
                "europe_pmc": 1.2,
                "arxiv": 0.4,
                "biorxiv": 1.3,
            },
            "preprint_source": "biorxiv",
        },
    },
    "automation": {
        "auto_refresh_indexes": True,
        "git_commit": False,
        "git_push": False,
        "save_phase_outputs": True,
    },
    # Backward compatibility for old scripts that still consume daily_papers block.
    "daily_papers": {
        "keywords": [
            "world model",
            "diffusion model",
            "embodied ai",
            "3d gaussian splatting",
            "4d gaussian splatting",
            "sim-to-real",
            "sim2real",
            "robot simulation",
        ],
        "negative_keywords": [
            "medical imaging",
            "weather forecast",
            "climate",
            "pet restoration",
            "mri",
            "ct scan",
            "pathology",
            "diagnosis",
            "protein",
            "drug discovery",
            "molecular",
            "audio generation",
            "music generation",
            "speech synthesis",
            "text-to-speech",
            "speech recognition",
            "voice cloning",
            "coding agent",
            "code agent",
            "code generation",
            "software engineering agent",
            "gui agent",
            "computer use",
            "web agent",
            "browser agent",
            "document parsing",
            "document understanding",
            "ocr",
            "rag framework",
            "retrieval augmented",
            "retrieval-augmented",
            "llm memory",
            "long-term memory for llm",
            "text-to-sql",
            "code repair",
            "code review",
            "trading",
            "financial",
        ],
        "domain_boost_keywords": [
            "robot",
            "manipulation",
            "grasping",
            "locomotion",
            "navigation",
            "planning",
            "reinforcement learning",
            "policy learning",
            "visuomotor",
            "action prediction",
        ],
        "arxiv_categories": ["cs.RO", "cs.CV", "cs.AI", "cs.LG"],
        "min_score": 2,
        "top_n": 30,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _ensure_list(value: object) -> list:
    if isinstance(value, list):
        return value
    return []


def _migrate_legacy_daily_papers(config: dict) -> None:
    """Bridge old `daily_papers` config into domain/profile-aware config.

    This keeps older scripts functional during staged migration while new modules
    consume `active_domain` + `domain_profiles`.
    """

    legacy = config.get("daily_papers")
    if not isinstance(legacy, dict):
        return

    profiles = config.setdefault("domain_profiles", {})
    ic = profiles.setdefault("intelligent_construction", {})

    # Fill only missing values; explicit domain profile settings win.
    if not ic.get("queries"):
        ic["queries"] = _ensure_list(legacy.get("keywords"))
    if not ic.get("positive_keywords"):
        ic["positive_keywords"] = _ensure_list(legacy.get("keywords"))
    if not ic.get("negative_keywords"):
        ic["negative_keywords"] = _ensure_list(legacy.get("negative_keywords"))
    if not ic.get("boost_keywords"):
        ic["boost_keywords"] = _ensure_list(legacy.get("domain_boost_keywords"))
    ic.setdefault("source_preferences", {})
    ic.setdefault("preprint_source", "arxiv")

    preprint_sources = (
        config.setdefault("preprint_channel", {})
        .setdefault("sources", {})
        .setdefault("arxiv", {})
    )
    if not preprint_sources.get("categories"):
        preprint_sources["categories"] = _ensure_list(legacy.get("arxiv_categories"))


@lru_cache(maxsize=1)
def load_user_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_dir = Path(__file__).resolve().parent

    for filename in ("user-config.json", "user-config.local.json"):
        config_path = config_dir / filename
        if not config_path.exists():
            continue
        with config_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            _deep_merge(config, loaded)

    _migrate_legacy_daily_papers(config)

    if config.get("active_domain") not in config.get("domain_profiles", {}):
        config["active_domain"] = "intelligent_construction"

    return config


def _expand(path_value: str) -> Path:
    return Path(path_value).expanduser()


def paths_config() -> dict:
    return load_user_config()["paths"]


def active_domain() -> str:
    return str(load_user_config().get("active_domain", "intelligent_construction"))


def domain_profiles_config() -> dict:
    return load_user_config().get("domain_profiles", {})


def active_domain_profile() -> dict:
    profiles = domain_profiles_config()
    name = active_domain()
    return profiles.get(name, profiles.get("intelligent_construction", {}))


def published_channel_config() -> dict:
    return load_user_config().get("published_channel", {})


def preprint_channel_config() -> dict:
    return load_user_config().get("preprint_channel", {})


def daily_papers_config() -> dict:
    """Backward-compatible view for legacy single-channel scripts.

    During migration, old scripts still use this function. We synthesize values
    from the active domain profile whenever possible.
    """

    config = load_user_config()
    legacy = config.get("daily_papers", {})
    profile = active_domain_profile()

    keywords = list(
        dict.fromkeys(
            _ensure_list(profile.get("queries"))
            + _ensure_list(profile.get("positive_keywords"))
        )
    )
    if not keywords:
        keywords = _ensure_list(legacy.get("keywords"))

    negative_keywords = _ensure_list(profile.get("negative_keywords")) or _ensure_list(
        legacy.get("negative_keywords")
    )
    boost_keywords = _ensure_list(profile.get("boost_keywords")) or _ensure_list(
        legacy.get("domain_boost_keywords")
    )

    arxiv_categories = (
        preprint_channel_config()
        .get("sources", {})
        .get("arxiv", {})
        .get("categories", _ensure_list(legacy.get("arxiv_categories")))
    )

    return {
        "keywords": keywords,
        "negative_keywords": negative_keywords,
        "domain_boost_keywords": boost_keywords,
        "arxiv_categories": arxiv_categories,
        "min_score": int(legacy.get("min_score", 2)),
        "top_n": int(legacy.get("top_n", 30)),
    }


def automation_config() -> dict:
    config = load_user_config().get("automation", {})
    if config.get("git_push") and not config.get("git_commit"):
        config = copy.deepcopy(config)
        config["git_push"] = False
    return config


def obsidian_vault_path() -> Path:
    return _expand(paths_config()["obsidian_vault"])


def paper_notes_dir() -> Path:
    return obsidian_vault_path() / paths_config()["paper_notes_folder"]


def daily_papers_dir() -> Path:
    return obsidian_vault_path() / paths_config()["daily_papers_folder"]


def concepts_dir() -> Path:
    return paper_notes_dir() / paths_config()["concepts_folder"]


def zotero_db_path() -> Path:
    return _expand(paths_config()["zotero_db"])


def zotero_storage_dir() -> Path:
    return _expand(paths_config()["zotero_storage"])


def auto_refresh_indexes_enabled() -> bool:
    return bool(automation_config().get("auto_refresh_indexes", True))


def git_commit_enabled() -> bool:
    return bool(automation_config().get("git_commit", False))


def git_push_enabled() -> bool:
    return bool(automation_config().get("git_push", False))
