#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from _figure_common import paper_id_from_inputs, pdftotext_pages, slugify
from _paper_reader_runtime import load_state, notes_dir
from run_figure_pipeline import run_pipeline


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _pdf_metadata(pdf_path: Path) -> dict[str, Any]:
    try:
        import fitz  # type: ignore

        with fitz.open(str(pdf_path)) as doc:
            meta = doc.metadata or {}
            first_page_text = (
                doc.load_page(0).get_text("text") if doc.page_count else ""
            )
        return {
            "title": str(meta.get("title") or "").strip(),
            "author": str(meta.get("author") or "").strip(),
            "subject": str(meta.get("subject") or "").strip(),
            "keywords": str(meta.get("keywords") or "").strip(),
            "first_page_text": first_page_text,
        }
    except Exception:
        return {
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "first_page_text": "",
        }


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _extract_year(record: dict[str, Any], text: str) -> str:
    year = record.get("year")
    if year:
        return str(year)
    published_date = str(record.get("published_date", "")).strip()
    match = re.search(r"(19|20)\d{2}", published_date)
    if match:
        return match.group(0)
    match = re.search(r"\b(19|20)\d{2}\b", text[:2000])
    return match.group(0) if match else ""


def _sentence_chunks(text: str, limit: int = 3) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?。；;])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()][:limit]


def _problem_text(record: dict[str, Any], text: str) -> str:
    abstract = _first_nonempty(record.get("abstract"), text[:1500])
    sentences = _sentence_chunks(abstract, limit=2)
    return (
        " ".join(sentences)
        if sentences
        else "论文主要关注的问题需要结合原文进一步确认。"
    )


def _method_text(record: dict[str, Any], text: str) -> str:
    return _first_nonempty(
        record.get("core_method"),
        record.get("method_summary"),
        record.get("sharp_commentary"),
        "正文可用信息有限，建议重点回看方法章节与模型框架图。",
    )


def _main_findings(record: dict[str, Any], text: str) -> list[str]:
    findings = _listify(record.get("experiment_clues"))
    if not findings:
        findings = _sentence_chunks(
            _first_nonempty(record.get("abstract"), text), limit=3
        )
    if not findings:
        findings = ["主要结果需要回看原文实验部分确认。"]
    return findings[:3]


def _data_eval_notes(record: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for label, key in [
        ("实验线索", "experiment_clues"),
        ("真实场景线索", "real_world_clues"),
        ("仿真线索", "simulation_clues"),
        ("对比基线", "baseline_candidates"),
    ]:
        values = _listify(record.get(key))
        if values:
            notes.append(f"{label}: {'; '.join(values[:4])}")
    return notes or ["数据集、评测协议或基线信息提取有限，建议回看实验设置章节。"]


def _limitations(record: dict[str, Any]) -> list[str]:
    missing = (
        record.get("missing_field_report", {})
        if isinstance(record.get("missing_field_report"), dict)
        else {}
    )
    items = [f"{key}: {value}" for key, value in list(missing.items())[:3]]
    if not items:
        items = ["当前笔记基于可提取文本整理，细节仍需结合原文图表与附录核对。"]
    return items


def _inspirations(record: dict[str, Any]) -> list[str]:
    inspirations = [
        _first_nonempty(record.get("borrowing_value")),
        _first_nonempty(record.get("inspiration_notes")),
    ]
    values = [item for item in inspirations if item]
    return values[:2] or ["可优先借鉴其问题建模方式、实验对比设计和方法模块拆分。"]


def _linked_concepts(record: dict[str, Any]) -> list[str]:
    concepts = []
    for item in _listify(record.get("method_names"))[:6]:
        label = item.replace("[", "").replace("]", "").strip()
        if label:
            concepts.append(f"[[{label}]]")
    return concepts or ["[[]]"]


def _missing_rows(record: dict[str, Any]) -> list[str]:
    missing = (
        record.get("missing_field_report", {})
        if isinstance(record.get("missing_field_report"), dict)
        else {}
    )
    if not missing:
        return [
            "| image_enhancement | info | Text-first mode keeps note generation available even when figures are skipped |"
        ]
    return [
        f"| {key} | missing | {str(value).replace('|', '/')} |"
        for key, value in missing.items()
    ]


def _source_notes(
    record: dict[str, Any], pdf_path: Path | None, image_status: str
) -> list[str]:
    route = (
        "local_pdf"
        if pdf_path
        else _first_nonempty(
            record.get("preferred_fulltext_input_type"), "metadata_only"
        )
    )
    route_value = (
        str(pdf_path)
        if pdf_path
        else _first_nonempty(
            record.get("preferred_fulltext_input_value"), record.get("url"), ""
        )
    )
    return [
        f"Full-text route: {route}",
        f"Full-text source: {route_value or 'unavailable'}",
        f"Figure manifest: {image_status}",
        f"Image enhancement: {image_status}",
        f"Extraction notes: {'; '.join(_listify(record.get('extraction_notes'))) or 'No extra extraction notes'}",
    ]


def _render_note(
    record: dict[str, Any],
    pdf_path: Path | None,
    paper_id: str,
    text: str,
    image_status: str,
) -> str:
    title = _first_nonempty(record.get("title"), record.get("pdf_title"), paper_id)
    authors = _listify(record.get("authors"))
    year = _extract_year(record, text)
    source = _first_nonempty(record.get("source"), record.get("channel"), "")
    venue = _first_nonempty(record.get("venue"), record.get("publication_type"), "")
    doi = _first_nonempty(record.get("doi"))
    url = _first_nonempty(record.get("url"), record.get("pdf_url"))
    zotero_collection = _first_nonempty(record.get("zotero_collection"), "_待整理")
    one_line = _first_nonempty(
        record.get("core_method"), record.get("method_summary"), record.get("abstract")
    )
    one_line = _sentence_chunks(one_line, limit=1)
    summary = (
        one_line[0] if one_line else "本文的核心贡献需要结合方法与实验章节进一步凝练。"
    )
    key_components = _listify(record.get("method_names"))[:5] or [
        "需结合方法章节补充模块拆解"
    ]
    findings = _main_findings(record, text)
    data_eval = _data_eval_notes(record)
    limitations = _limitations(record)
    inspirations = _inspirations(record)
    linked = _linked_concepts(record)
    source_notes = _source_notes(record, pdf_path, image_status)
    missing_rows = _missing_rows(record)
    formula = _first_nonempty(record.get("key_formula"))
    if not formula:
        formula = "未稳定提取到关键公式；如该论文以明确损失函数或状态转移方程为核心，建议回看方法章节原文。"

    lines = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"authors: {json.dumps(authors, ensure_ascii=False)}",
        f"year: {year or ''}",
        f"source: {source}",
        f"venue: {venue}",
        f"doi: {doi}",
        f"url: {url}",
        f"arxiv_id: {record.get('source_id', '') if str(record.get('source', '')).lower() == 'arxiv' else ''}",
        f"zotero_collection: {zotero_collection}",
        f"tags: [paper]",
        f"domain: {record.get('domain', '')}",
        "image_source: vault_local",
        f"extraction_confidence: {record.get('extraction_confidence', '')}",
        f"created: {date.today().isoformat()}",
        "---",
        "",
        f"# {title}",
        "",
        "## Paper Snapshot",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Authors | {', '.join(authors)} |",
        f"| Year | {year} |",
        f"| Source | {source} {venue} |",
        f"| DOI / URL | {doi or url} |",
        f"| Zotero | {zotero_collection} |",
        "",
        "## One-Line Summary",
        "",
        f"> {summary}",
        "",
        "## Research Problem",
        "",
        _problem_text(record, text),
        "",
        "## Method Summary",
        "",
        _method_text(record, text),
        "",
        "### Key Components",
        "",
    ]
    lines.extend([f"- {item}" for item in key_components])
    lines.extend(
        [
            "",
            "## 关键图示 (Key Figures)",
            "",
            f"- 图像模式: {image_status}",
            "- 图像覆盖: 待图像增强阶段补充；若不可用则保持 text-only。",
            "",
            "### 方法 / 框架图",
            "",
            "- 未提取时保留简洁状态说明，不阻断正文研究笔记。",
            "",
            "### 核心结果图",
            "",
            "- 成功提取时优先保留 1 张最关键结果图；失败时写明缺失。",
            "",
            "## 全部候选图 (All Candidate Figures)",
            "",
            "- 图像覆盖：待补充",
            "- 建议关注图：方法框架图、模型结构图、主结果图",
            "",
            "## Key Formula",
            "",
            "```text",
            formula,
            "```",
            "",
            "## Main Findings",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in findings])
    lines.extend(["", "## Notes on Data / Evaluation", ""])
    lines.extend([f"- {item}" for item in data_eval])
    lines.extend(["", "## Limitations", ""])
    lines.extend([f"- {item}" for item in limitations])
    lines.extend(["", "## Inspiration for My Research", ""])
    lines.extend([f"- {item}" for item in inspirations])
    lines.extend(["", "## Linked Concepts", ""])
    lines.extend([f"- {item}" for item in linked])
    lines.extend(
        [
            "",
            "## Missing Field Report",
            "",
            "| Field | Status | Reason |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(missing_rows)
    lines.extend(["", "## Source Notes", ""])
    lines.extend([f"- {item}" for item in source_notes])
    lines.append("")
    return "\n".join(lines)


def _note_filename(title: str, paper_id: str) -> str:
    candidate = title.strip().replace("/", "-").replace("\\", "-").replace(":", " -")
    candidate = re.sub(r"[<>\"|?*]", "", candidate).strip().rstrip(".")
    if not candidate:
        candidate = slugify(paper_id, default="paper")
    return candidate


def _merge_record_with_pdf_metadata(
    record: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(record)
    if not merged.get("title"):
        merged["title"] = metadata.get("title", "")
    if not merged.get("authors") and metadata.get("author"):
        merged["authors"] = [
            part.strip()
            for part in re.split(r"[;,]", metadata["author"])
            if part.strip()
        ]
    return merged


def run_reader(
    pdf_path: Path | None = None,
    record: dict[str, Any] | None = None,
    paper_id: str = "",
) -> dict[str, Any]:
    payload = record or {}
    pdf_meta = _pdf_metadata(pdf_path) if pdf_path else {}
    payload = _merge_record_with_pdf_metadata(payload, pdf_meta)
    resolved_paper_id = paper_id_from_inputs(
        paper_id or str(payload.get("paper_id", "")),
        pdf_path or payload.get("title", "paper"),
    )
    pages = pdftotext_pages(pdf_path) if pdf_path else []
    text = "\n\n".join(page for page in pages if page).strip()
    if not text:
        text = _first_nonempty(
            payload.get("abstract"), pdf_meta.get("first_page_text", "")
        )

    note_title = _first_nonempty(payload.get("title"), resolved_paper_id)
    note_path = notes_dir() / f"{_note_filename(note_title, resolved_paper_id)}.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    state = load_state()
    image_status = "text_only"
    note_text = _render_note(payload, pdf_path, resolved_paper_id, text, image_status)
    note_path.write_text(note_text, encoding="utf-8")

    image_result: dict[str, Any] | None = None
    if pdf_path and state.get("user_opt_in") == "yes" and state.get("backend_ready"):
        image_result = run_pipeline(pdf_path, resolved_paper_id, note_path)
        image_status = str(image_result.get("image_mode", "text_only"))
    else:
        image_result = {
            "status": "skipped",
            "image_mode": "text_only",
            "reason": "Image enhancement not enabled or backend unavailable",
        }

    if image_status != "text_only":
        note_text = note_path.read_text(encoding="utf-8")
    else:
        note_text = _render_note(
            payload, pdf_path, resolved_paper_id, text, image_status
        )
        note_path.write_text(note_text, encoding="utf-8")

    return {
        "status": "ok",
        "paper_id": resolved_paper_id,
        "note_path": str(note_path),
        "text_ready": True,
        "image": image_result,
        "needs_image_setup_prompt": state.get("user_opt_in") == "unknown",
        "recommended_image_setup_prompt": "检测到这是你首次使用论文图像增强功能。我可以做一次性初始化，后续可自动补充关键方法图和结果图。本次即使不配置，我也会先正常输出论文研究笔记。是否现在配置？",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", nargs="?", default="")
    parser.add_argument("--record-json", default="")
    parser.add_argument("--paper-id", default="")
    args = parser.parse_args()

    record = _read_json(Path(args.record_json)) if args.record_json else {}
    pdf_path = Path(args.pdf_path).expanduser().resolve() if args.pdf_path else None
    payload = run_reader(pdf_path, record, args.paper_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
