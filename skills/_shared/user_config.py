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
    "active_domain": "geo_timeseries_fm",
    "published_channel": {
        "enabled": True,
        "backend": "paper_fetcher",
        "recall_n": 200,
        "lite_n": 50,
        "pdf_n": 20,
        "rich_n": 20,
        "auto_continue_without_pdf": False,
        "providers": [
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
                "categories": ["cs.RO", "cs.AI", "cs.LG", "eess.SP"],
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
        "geo_timeseries_fm": {
            "queries": [
                "geotechnical time series forecasting",
                "deep excavation deformation prediction",
                "foundation pit settlement prediction",
                "tunnel settlement spatiotemporal forecasting",
                "uncertainty-aware geotechnical forecasting foundation model",
            ],
            "positive_keywords": [
                "geotechnical",
                "deep excavation",
                "foundation pit",
                "tunnel settlement",
                "deformation prediction",
                "time series forecasting",
                "spatiotemporal forecasting",
                "uncertainty-aware",
                "probabilistic forecasting",
                "interval prediction",
                "quantile prediction",
                "foundation model",
                "pretrained model",
                "large time-series model",
                "risk assessment",
                "early warning",
            ],
            "negative_keywords": [
                "medical imaging",
                "clinical",
                "genomics",
                "protein",
                "drug discovery",
                "epidemic",
                "monsoon",
                "rocket",
                "ignition",
                "humanoid locomotion",
                "robotic manipulation",
                "speech synthesis",
                "speech recognition",
                "audio generation",
                "financial forecasting",
                "stock market",
                "trading",
                "text-to-sql",
                "gui agent",
            ],
            "boost_keywords": [
                "field monitoring",
                "site data",
                "inclinometer",
                "settlement",
                "displacement",
                "uncertainty quantification",
                "probabilistic risk",
                "warning threshold",
            ],
            "source_preferences": {
                "openalex": 1.1,
                "crossref": 1.0,
                "pubmed": 0.1,
                "europe_pmc": 0.1,
                "arxiv": 1.2,
                "biorxiv": 0.1,
            },
            "preprint_source": "arxiv",
        },
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
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


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

    if config.get("active_domain") not in config.get("domain_profiles", {}):
        config["active_domain"] = "geo_timeseries_fm"

    return config


def _expand(path_value: str) -> Path:
    return Path(path_value).expanduser()


def paths_config() -> dict:
    return load_user_config()["paths"]


def active_domain() -> str:
    return str(load_user_config().get("active_domain", "geo_timeseries_fm"))


def domain_profiles_config() -> dict:
    return load_user_config().get("domain_profiles", {})


def active_domain_profile() -> dict:
    profiles = domain_profiles_config()
    name = active_domain()
    return profiles.get(name, profiles.get("geo_timeseries_fm", {}))


def published_channel_config() -> dict:
    return load_user_config().get("published_channel", {})


def preprint_channel_config() -> dict:
    return load_user_config().get("preprint_channel", {})


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
