#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_PATH = SKILL_DIR / "paper-reader.local.json"
EXAMPLE_CONFIG_PATH = SKILL_DIR / "paper-reader.config.example.json"
STATE_PATH = SKILL_DIR / "image_pipeline_state.json"
LEGACY_STATE_PATH = SKILL_DIR / "paper-reader.state.json"
TEMP_ROOT = SKILL_DIR / ".temp-output"


DEFAULT_LOCAL_CONFIG = {
    "paths": {
        "output_root": "",
        "paper_notes_folder": "论文笔记",
        "assets_folder": "assets/papers",
    },
    "image_enhancement": {
        "enabled": True,
        "auto_setup_images": False,
        "preferred_backend": "pymupdf",
    },
}


DEFAULT_STATE = {
    "initialized": False,
    "user_opt_in": "unknown",
    "backend": "none",
    "backend_ready": False,
    "last_check_time": "",
    "last_error": "",
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)
    return data if isinstance(data, type(default)) else copy.deepcopy(default)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def example_config() -> dict:
    return _read_json(EXAMPLE_CONFIG_PATH, {})


def local_config_exists() -> bool:
    return LOCAL_CONFIG_PATH.exists()


def load_local_config() -> dict:
    config = copy.deepcopy(DEFAULT_LOCAL_CONFIG)
    loaded = _read_json(LOCAL_CONFIG_PATH, {})
    if isinstance(loaded, dict):
        _deep_merge(config, loaded)
    return config


def load_state() -> dict:
    state = copy.deepcopy(DEFAULT_STATE)
    loaded = _read_json(STATE_PATH, {})
    if not loaded and LEGACY_STATE_PATH.exists():
        loaded = _read_json(LEGACY_STATE_PATH, {})
    if isinstance(loaded, dict):
        if "image_backend" in loaded and "backend" not in loaded:
            loaded["backend"] = loaded.get("image_backend", "none")
        _deep_merge(state, loaded)
    return state


def save_state(state: dict) -> dict:
    payload = copy.deepcopy(DEFAULT_STATE)
    _deep_merge(payload, state)
    _write_json(STATE_PATH, payload)
    return payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def runtime_mode() -> str:
    return "configured" if local_config_exists() else "temporary"


def output_root() -> Path:
    config = load_local_config()
    raw_output_root = str(config.get("paths", {}).get("output_root", "")).strip()
    if raw_output_root:
        return Path(raw_output_root).expanduser().resolve()
    return TEMP_ROOT.resolve()


def notes_dir() -> Path:
    config = load_local_config()
    folder = (
        str(config.get("paths", {}).get("paper_notes_folder", "论文笔记")).strip()
        or "论文笔记"
    )
    return output_root() / folder


def paper_assets_dir(paper_id: str) -> Path:
    config = load_local_config()
    assets_folder = (
        str(config.get("paths", {}).get("assets_folder", "assets/papers")).strip()
        or "assets/papers"
    )
    return output_root() / Path(assets_folder) / paper_id / "figures"


def obsidian_relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(output_root()).as_posix()
    except Exception:
        return path.name


def detect_image_backend() -> dict:
    image_config = load_local_config().get("image_enhancement", {})
    if not bool(image_config.get("enabled", True)):
        return {
            "backend": "none",
            "backend_ready": False,
            "available_backends": [],
            "details": {
                "pymupdf": {"available": False, "error": "disabled by config"},
                "poppler": {},
            },
            "error": "Image enhancement disabled by local config",
        }

    preferred = str(image_config.get("preferred_backend", "pymupdf")).lower()
    pymupdf_ready = False
    pymupdf_error = ""
    try:
        import fitz  # type: ignore  # noqa: F401

        pymupdf_ready = True
    except Exception as exc:
        pymupdf_error = str(exc)

    poppler = {
        "pdfimages": shutil.which("pdfimages") is not None,
        "pdftoppm": shutil.which("pdftoppm") is not None,
        "pdftotext": shutil.which("pdftotext") is not None,
    }
    poppler_ready = poppler["pdfimages"] or poppler["pdftoppm"] or poppler["pdftotext"]
    available_backends: list[str] = []
    if pymupdf_ready:
        available_backends.append("pymupdf")
    if poppler_ready:
        available_backends.append("poppler")

    backend = "none"
    backend_ready = False
    if preferred == "poppler" and poppler_ready:
        backend = "poppler"
        backend_ready = True
    elif pymupdf_ready:
        backend = "pymupdf"
        backend_ready = True
    elif poppler_ready:
        backend = "poppler"
        backend_ready = True

    details = {
        "pymupdf": {"available": pymupdf_ready, "error": pymupdf_error},
        "poppler": poppler,
    }
    error = ""
    if not backend_ready:
        error = pymupdf_error or "No image backend available"
    return {
        "backend": backend,
        "backend_ready": backend_ready,
        "available_backends": available_backends,
        "details": details,
        "error": error,
    }


def update_state_from_probe(mark_initialized: bool = False) -> dict:
    state = load_state()
    probe = detect_image_backend()
    state.update(
        {
            "backend": probe["backend"],
            "backend_ready": probe["backend_ready"],
            "last_check_time": utc_now_iso(),
            "last_error": probe["error"],
        }
    )
    if mark_initialized:
        state["initialized"] = True
    save_state(state)
    return state


def set_user_choice(choice: str) -> dict:
    normalized = choice.strip().lower()
    if normalized not in {"yes", "no", "unknown"}:
        normalized = "unknown"
    state = load_state()
    state["user_opt_in"] = normalized
    state["initialized"] = normalized != "unknown"
    state["last_check_time"] = utc_now_iso()
    if normalized == "no":
        state["backend"] = "none"
        state["backend_ready"] = False
        state["last_error"] = ""
    save_state(state)
    return state


def reset_state() -> dict:
    return save_state(copy.deepcopy(DEFAULT_STATE))
