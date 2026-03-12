#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _figure_common import manifest_path_for_paper, paper_id_from_inputs, read_json


FIGURES_SECTION = "## Figures"


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


def _coverage_line(figures: list[dict]) -> str:
    has_method = any(
        item.get("estimated_role") in {"framework", "method"} for item in figures
    )
    has_result = any(item.get("estimated_role") == "result" for item in figures)
    if has_method and has_result:
        return "图像覆盖：方法图✓ 结果图✓"
    if has_method:
        return "图像覆盖：方法图✓ 结果图-"
    if has_result:
        return "图像覆盖：方法图- 结果图✓"
    return "图像覆盖：未提取"


def render_figures_section(manifest: dict) -> str:
    figures = list(manifest.get("figures", []))
    fallback_reasons = list(manifest.get("fallback", {}).get("reasons", []))
    image_mode = manifest.get("image_mode", "none")
    recommended = list(manifest.get("recommended_figure_types", []))

    method_figure = _pick_first(figures, {"framework", "method"})
    result_figure = _pick_first(figures, {"result"})

    lines = [FIGURES_SECTION, "", _coverage_line(figures)]

    if image_mode == "none":
        lines.append("建议关注图：")
        for item in recommended:
            lines.append(f"- {item}")
        if fallback_reasons:
            lines.append(f"- 说明：{'; '.join(fallback_reasons)}")
        return "\n".join(lines)

    lines.append("关键图：")
    if method_figure:
        label = (
            method_figure.get("caption_snippet")
            or f"Fig{method_figure['page_number']} 方法结构"
        )
        lines.append(f"- {label}")
        lines.append(f"![[{method_figure['vault_relpath']}]]")
    if result_figure:
        label = (
            result_figure.get("caption_snippet")
            or f"Fig{result_figure['page_number']} 主结果"
        )
        lines.append(f"- {label}")
        lines.append(f"![[{result_figure['vault_relpath']}]]")

    if image_mode == "partial":
        missing_labels = []
        if not method_figure:
            missing_labels.append("方法图")
        if not result_figure:
            missing_labels.append("结果图")
        if missing_labels:
            lines.append(f"- 缺失图像：{'、'.join(missing_labels)}")
    if fallback_reasons:
        lines.append(f"- 说明：{'; '.join(fallback_reasons)}")
    return "\n".join(lines)


def link_figures(note_path: Path, manifest_path: Path) -> bool:
    manifest = read_json(manifest_path, {})
    content = note_path.read_text(encoding="utf-8")
    content = replace_section(
        content, FIGURES_SECTION, render_figures_section(manifest)
    )
    content = replace_section(
        content, "## 关键图示 (Key Figures)", render_figures_section(manifest)
    )
    content = re.sub(
        r"\n## 全部候选图 \(All Candidate Figures\)\n.*?(?=\n## |\Z)",
        "\n",
        content,
        flags=re.DOTALL,
    )
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
