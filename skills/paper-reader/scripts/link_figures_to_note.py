#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _figure_common import manifest_path_for_paper, paper_id_from_inputs, read_json


KEY_SECTION = "## 关键图示 (Key Figures)"
ALL_SECTION = "## 全部候选图 (All Candidate Figures)"


def replace_section(text: str, heading: str, content: str) -> str:
    pattern = re.compile(rf"{re.escape(heading)}\n.*?(?=\n## |\Z)", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(content.rstrip() + "\n", text)
    return text.rstrip() + "\n\n" + content.rstrip() + "\n"


def _pick_first(figures: list[dict], roles: set[str]) -> dict | None:
    for item in figures:
        if item.get("estimated_role") in roles and item.get("vault_relpath"):
            return item
    return None


def render_key_section(manifest: dict) -> str:
    figures = list(manifest.get("figures", []))
    fallback_reasons = list(manifest.get("fallback", {}).get("reasons", []))
    image_mode = manifest.get("image_mode", "text_only")
    recommended = list(manifest.get("recommended_figure_types", []))
    stats = manifest.get("stats", {})

    method_figure = _pick_first(figures, {"framework", "method"})
    result_figure = _pick_first(figures, {"result"})

    lines = [
        KEY_SECTION,
        "",
        f"- 图像模式: {image_mode}",
        f"- 图像覆盖: {stats.get('total_candidate_figures', 0)} 个候选图，关键方法/框架图 {stats.get('key_method_framework_figures', 0)} 张，关键结果图 {stats.get('key_result_figures', 0)} 张",
    ]
    if fallback_reasons:
        lines.append(f"- 图像说明: {'; '.join(fallback_reasons)}")

    lines.extend(["", "### 方法 / 框架图", ""])
    if method_figure:
        lines.append(f"- Page {method_figure['page_number']} | {method_figure['source_type']} | {method_figure['extraction_confidence']}")
        if method_figure.get("caption_snippet"):
            lines.append(f"  {method_figure['caption_snippet']}")
        lines.append(f"  ![[{method_figure['vault_relpath']}]]")
    else:
        lines.append("- 未提取到稳定的方法图。")

    lines.extend(["", "### 核心结果图", ""])
    if result_figure:
        lines.append(f"- Page {result_figure['page_number']} | {result_figure['source_type']} | {result_figure['extraction_confidence']}")
        if result_figure.get("caption_snippet"):
            lines.append(f"  {result_figure['caption_snippet']}")
        lines.append(f"  ![[{result_figure['vault_relpath']}]]")
    else:
        lines.append("- 未提取到稳定的主结果图。")

    if not figures and recommended:
        lines.extend(["", "### 建议关注图", "", f"- {', '.join(recommended)}"])
    return "\n".join(lines)


def render_all_candidates(manifest: dict) -> str:
    figures = [item for item in manifest.get("figures", []) if item.get("vault_relpath")]
    recommended = list(manifest.get("recommended_figure_types", []))
    lines = [ALL_SECTION, ""]
    if not figures:
        lines.append("- 图像覆盖：未提取")
        if recommended:
            lines.append(f"- 建议关注图：{', '.join(recommended)}")
        return "\n".join(lines)

    preview = figures[:6]
    for item in preview:
        lines.append(f"- Page {item['page_number']} | {item['estimated_role']} | {item['source_type']} | {item['extraction_confidence']}")
        lines.append(f"  ![[{item['vault_relpath']}]]")
    remaining = len(figures) - len(preview)
    if remaining > 0:
        lines.append(f"- 其余 {remaining} 张候选图已保存在图像目录中，可按需展开。")
    return "\n".join(lines)


def link_figures(note_path: Path, manifest_path: Path) -> bool:
    manifest = read_json(manifest_path, {})
    content = note_path.read_text(encoding="utf-8")
    content = replace_section(content, KEY_SECTION, render_key_section(manifest))
    content = replace_section(content, ALL_SECTION, render_all_candidates(manifest))
    note_path.write_text(content, encoding="utf-8")
    return bool(manifest.get("figures"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("note_path")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--paper-id", default="")
    parser.add_argument("--pdf-path", default="")
    args = parser.parse_args()

    note_path = Path(args.note_path).expanduser().resolve()
    if args.manifest_path:
        manifest_path = Path(args.manifest_path).expanduser().resolve()
    else:
        paper_id = paper_id_from_inputs(args.paper_id, args.pdf_path or note_path.stem)
        manifest_path = manifest_path_for_paper(paper_id)
    link_figures(note_path, manifest_path)


if __name__ == "__main__":
    main()
