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


def render_key_section(figures: list[dict], fallback_reasons: list[str]) -> str:
    method_figures = [
        item
        for item in figures
        if item.get("estimated_role") in {"framework", "method"}
        and item.get("vault_relpath")
    ]
    result_figures = [
        item
        for item in figures
        if item.get("estimated_role") == "result" and item.get("vault_relpath")
    ]

    lines = [KEY_SECTION, "", "### 方法 / 框架图", ""]
    if method_figures:
        for item in method_figures:
            lines.append(
                f"- Page {item['page_number']} | {item['source_type']} | {item['extraction_confidence']}"
            )
            lines.append(f"  {item.get('caption_snippet', '')}".rstrip())
            lines.append(f"  ![[{item['vault_relpath']}]]")
    else:
        lines.append(
            "- No clean method/framework figure was extracted; rendered full-page fallback should be preserved if available."
        )

    lines.extend(["", "### 核心结果图", ""])
    if result_figures:
        for item in result_figures:
            lines.append(
                f"- Page {item['page_number']} | {item['source_type']} | {item['extraction_confidence']}"
            )
            lines.append(f"  {item.get('caption_snippet', '')}".rstrip())
            lines.append(f"  ![[{item['vault_relpath']}]]")
    else:
        lines.append(
            "- No clean result figure was extracted; rendered full-page fallback should be preserved if available."
        )

    if fallback_reasons:
        lines.extend(
            [
                "",
                "### 图像提取说明",
                "",
                f"- {'; '.join(fallback_reasons)}",
                "- PDF mainly uses vector or composite figures when full-page fallback dominates.",
            ]
        )
    return "\n".join(lines)


def render_all_candidates(figures: list[dict]) -> str:
    lines = [ALL_SECTION, ""]
    if not figures:
        lines.append("- No candidate figures were preserved.")
        return "\n".join(lines)

    current_page = None
    for item in figures:
        if not item.get("vault_relpath"):
            continue
        if item["page_number"] != current_page:
            current_page = item["page_number"]
            lines.extend([f"### Page {current_page}", ""])
        lines.append(
            f"- {item['estimated_role']} | {item['source_type']} | confidence={item['extraction_confidence']}"
        )
        if item.get("caption_snippet"):
            lines.append(f"  {item['caption_snippet']}")
        lines.append(f"  ![[{item['vault_relpath']}]]")
    return "\n".join(lines)


def link_figures(note_path: Path, manifest_path: Path) -> bool:
    manifest = read_json(manifest_path, {})
    figures = list(manifest.get("figures", []))
    fallback_reasons = list(manifest.get("fallback", {}).get("reasons", []))
    content = note_path.read_text(encoding="utf-8")
    content = replace_section(
        content, KEY_SECTION, render_key_section(figures, fallback_reasons)
    )
    content = replace_section(content, ALL_SECTION, render_all_candidates(figures))
    note_path.write_text(content, encoding="utf-8")
    print(f"note linked with figures: {'yes' if figures else 'no'}")
    return bool(figures)


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
