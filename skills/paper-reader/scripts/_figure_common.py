#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from user_config import obsidian_vault_path


ROLE_KEYWORDS = {
    "framework": ["framework", "architecture", "overview", "system", "workflow"],
    "method": ["method", "pipeline", "approach", "module", "algorithm"],
    "result": [
        "result",
        "results",
        "experiment",
        "comparison",
        "ablation",
        "performance",
        "visualization",
    ],
    "supplementary": ["appendix", "supplementary", "additional", "extra"],
}

FIGURE_LIKE_KEYWORDS = sorted(
    {
        "figure",
        "fig.",
        "framework",
        "method",
        "pipeline",
        "architecture",
        "workflow",
        "experiment",
        "results",
        "comparison",
        "ablation",
        "visualization",
        "performance",
    }
)


def slugify(value: str, default: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return cleaned or default


def paper_id_from_inputs(paper_id: str | None, pdf_path: str | Path) -> str:
    if paper_id:
        return slugify(paper_id, default="paper")
    return slugify(Path(pdf_path).stem, default="paper")


def figures_dir_for_paper(paper_id: str) -> Path:
    return obsidian_vault_path() / "assets" / "papers" / paper_id / "figures"


def manifest_path_for_paper(paper_id: str) -> Path:
    return figures_dir_for_paper(paper_id) / "figure_manifest.json"


def vault_relpath(path: Path) -> str:
    return path.relative_to(obsidian_vault_path()).as_posix()


def wiki_link(path: Path) -> str:
    return f"![[{vault_relpath(path)}]]"


def png_dimensions(path: Path) -> tuple[int, int]:
    try:
        data = path.read_bytes()
    except Exception:
        return (0, 0)
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return (width, height)


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def pdftotext_pages(pdf_path: str | Path) -> list[str]:
    proc = run_command(["pdftotext", "-layout", str(pdf_path), "-"])
    if proc.returncode != 0:
        return []
    text = proc.stdout or ""
    return [page.strip() for page in text.split("\f")]


def page_keyword_hits(page_text: str) -> list[str]:
    lowered = page_text.lower()
    return [kw for kw in FIGURE_LIKE_KEYWORDS if kw in lowered]


def extract_caption_snippet(page_text: str) -> str:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for line in lines:
        if re.match(r"^(figure|fig\.?|table)\s*\d+", line, flags=re.IGNORECASE):
            return line[:240]
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in FIGURE_LIKE_KEYWORDS):
            return line[:240]
    return ""


def estimate_role(*texts: str) -> str:
    haystack = " ".join(texts).lower()
    best_role = "unknown"
    best_score = 0
    for role, keywords in ROLE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score > best_score:
            best_role = role
            best_score = score
    return best_role


def include_in_key_figures(role: str) -> bool:
    return role in {"framework", "method", "result"}


def confidence_label(source_type: str, role: str, caption_snippet: str) -> str:
    if source_type == "embedded" and caption_snippet:
        return "high"
    if source_type.startswith("rendered") and role in {"framework", "method", "result"}:
        return "medium"
    return "low"


def read_json(path: str | Path, default: Any) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
