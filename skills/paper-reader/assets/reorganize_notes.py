#!/usr/bin/env python3
"""Reorganize paper notes with lightweight domain-aware rules.

This script is intentionally simple:
- classify notes by active_domain
- move files into a smaller category tree
- optionally update the `zotero_collection` frontmatter field

It does not mutate the Zotero database.
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from user_config import active_domain, paper_notes_dir


PAPER_NOTES_ROOT = paper_notes_dir()

DOMAIN_RULES: dict[str, dict[str, list[str]]] = {
    "geo_timeseries_fm": {
        "1-岩土监测与预测": [
            "geotechnical",
            "foundation-pit",
            "tunnel",
            "settlement",
            "deformation",
            "forecasting",
            "prediction",
            "岩土",
            "基坑",
            "沉降",
        ],
        "2-时空与不确定性": [
            "spatiotemporal",
            "temporal",
            "uncertainty",
            "probabilistic",
            "quantile",
            "conformal",
            "时空",
            "不确定性",
        ],
        "3-基础模型与机器学习": [
            "foundation-model",
            "pretrained",
            "transformer",
            "deep-learning",
            "机器学习",
            "基础模型",
        ],
        "4-工程应用与数据": [
            "digital-twin",
            "monitoring",
            "sensor",
            "site-data",
            "数字孪生",
            "传感器",
        ],
        "5-Survey": ["survey", "review", "benchmark", "综述"],
    },
    "intelligent_construction": {
        "1-施工机器人与自动化": [
            "construction-robot",
            "autonomous-excavation",
            "robotics",
            "earthwork",
            "施工机器人",
            "自主施工",
        ],
        "2-岩土与安全监测": [
            "geotechnical",
            "foundation-pit",
            "monitoring",
            "safety",
            "early-warning",
            "岩土",
            "安全监测",
        ],
        "3-数字孪生与感知控制": [
            "digital-twin",
            "bim",
            "cim",
            "slam",
            "lidar",
            "control",
            "planning",
            "数字孪生",
            "感知",
            "控制",
        ],
        "4-基础模型与机器学习": [
            "foundation-model",
            "transformer",
            "deep-learning",
            "embodied-ai",
            "机器学习",
            "具身智能",
        ],
        "5-Survey": ["survey", "review", "benchmark", "综述"],
    },
    "biology": {
        "1-免疫与疾病机制": [
            "immune",
            "immunology",
            "cytokine",
            "inflammation",
            "clinical",
            "immune",
            "免疫",
            "临床",
        ],
        "2-组学与生物信息": [
            "single-cell",
            "transcriptomics",
            "genome",
            "bioinformatics",
            "sequence",
            "单细胞",
            "转录组",
            "生物信息",
        ],
        "3-蛋白质与分子设计": [
            "protein",
            "alphafold",
            "docking",
            "molecular",
            "drug-discovery",
            "蛋白质",
            "药物发现",
        ],
        "4-计算方法": [
            "transformer",
            "gnn",
            "vae",
            "deep-learning",
            "计算方法",
            "机器学习",
        ],
        "5-Survey": ["survey", "review", "benchmark", "综述"],
    },
}

GENERIC_RULES = {
    "1-方法": ["method", "model", "algorithm", "framework", "方法"],
    "2-应用": ["application", "deployment", "real-world", "应用"],
    "3-Survey": ["survey", "review", "综述"],
}


def get_rules() -> dict[str, list[str]]:
    domain = active_domain()
    if domain in DOMAIN_RULES:
        return DOMAIN_RULES[domain]
    for key, value in DOMAIN_RULES.items():
        if key in domain or domain in key:
            return value
    return GENERIC_RULES


def parse_frontmatter(path: Path) -> dict[str, Any] | None:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    return parse_simple_frontmatter(content[3:end].strip())


def parse_simple_frontmatter(frontmatter: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in frontmatter.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith((" ", "\t")):
            stripped = raw_line.strip()
            if current_list_key and stripped.startswith("- "):
                parsed.setdefault(current_list_key, []).append(
                    parse_scalar(stripped[2:].strip())
                )
            continue
        current_list_key = None
        if ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        value = strip_inline_comment(raw_value).strip()
        if not value:
            parsed[key] = []
            current_list_key = key
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            parsed[key] = [] if not inner else [
                parse_scalar(item) for item in next(csv.reader([inner], skipinitialspace=True))
            ]
            continue
        parsed[key] = parse_scalar(value)
    return parsed


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def strip_inline_comment(raw_value: str) -> str:
    in_single = False
    in_double = False
    for idx, char in enumerate(raw_value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return raw_value[:idx].rstrip()
    return raw_value.rstrip()


def determine_category(tags: list[str], title: str = "") -> str:
    rules = get_rules()
    if not tags and not title:
        return "_待整理"

    haystack = " ".join(str(t).lower() for t in tags) + " " + title.lower()
    best_category = "_待整理"
    best_score = 0

    for priority, (category, keywords) in enumerate(rules.items(), start=1):
        score = 0
        for keyword in keywords:
            if keyword.lower() in haystack:
                score += 2
        score += max(0, 10 - priority)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category if best_score > 0 else "_待整理"


def get_all_notes() -> list[Path]:
    notes: list[Path] = []
    for root, _, files in os.walk(PAPER_NOTES_ROOT):
        if "_概念" in root:
            continue
        for file_name in files:
            if file_name.endswith(".md"):
                notes.append(Path(root) / file_name)
    return notes


def update_frontmatter_collection(path: Path, category: str) -> None:
    content = path.read_text(encoding="utf-8")
    if "zotero_collection:" in content:
        content = re.sub(
            r"^zotero_collection:.*$",
            f"zotero_collection: {category}",
            content,
            flags=re.MULTILINE,
        )
    elif content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[:end] + f"zotero_collection: {category}\n" + content[end:]
    path.write_text(content, encoding="utf-8")


def reorganize_notes(dry_run: bool = True) -> list[tuple[Path, Path, str]]:
    notes = get_all_notes()
    moves: list[tuple[Path, Path, str]] = []

    print(f"当前领域: {active_domain()}")
    print(f"找到 {len(notes)} 篇论文笔记")

    for note in notes:
        frontmatter = parse_frontmatter(note)
        if not frontmatter:
            continue
        tags = frontmatter.get("tags", [])
        title = str(frontmatter.get("title", note.stem))
        category = determine_category(tags if isinstance(tags, list) else [], title)
        current_rel = note.relative_to(PAPER_NOTES_ROOT)
        current_dir = str(current_rel.parent)
        if current_dir.startswith(category):
            continue
        new_path = PAPER_NOTES_ROOT / category / note.name
        moves.append((note, new_path, category))

    print(f"需要移动 {len(moves)} 篇笔记")
    if dry_run:
        for old_path, new_path, category in moves:
            print(f"- {old_path.name}: {old_path.parent.name} -> {category}")
        print("[DRY RUN] 未实际执行移动，添加 --execute 执行")
        return moves

    for old_path, new_path, category in moves:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
        update_frontmatter_collection(new_path, category)
        print(f"已移动: {old_path.name} -> {category}/")

    return moves


def analyze_current_distribution() -> None:
    counts: dict[str, int] = {}
    for note in get_all_notes():
        frontmatter = parse_frontmatter(note)
        if not frontmatter:
            continue
        tags = frontmatter.get("tags", [])
        title = str(frontmatter.get("title", note.stem))
        category = determine_category(tags if isinstance(tags, list) else [], title)
        counts[category] = counts.get(category, 0) + 1

    print(f"当前领域: {active_domain()}")
    for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"{category}: {count}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        analyze_current_distribution()
    elif len(sys.argv) > 1 and sys.argv[1] == "--execute":
        reorganize_notes(dry_run=False)
    else:
        reorganize_notes(dry_run=True)
