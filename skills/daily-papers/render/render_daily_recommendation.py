#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
SHARED_DIR = DAILY_PAPERS_DIR.parent / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from user_config import daily_papers_dir, obsidian_vault_path


TMP_DIR = Path("/tmp")
PUBLISHED_LITE_PATH = TMP_DIR / "published_lite_50.json"
PUBLISHED_RICH_PATH = TMP_DIR / "published_review_rich_20.json"
PREPRINT_RICH_PATH = TMP_DIR / "preprint_review_rich_20.json"
MERGED_PATH = TMP_DIR / "daily_review_merged.json"

METHOD_PRIORITY_KEYWORDS = [
    "framework",
    "overview",
    "architecture",
    "pipeline",
    "workflow",
    "method",
    "system",
    "diagram",
    "model",
    "technical-route",
    "algorithm",
]
RESULT_PRIORITY_KEYWORDS = [
    "result",
    "experiment",
    "performance",
    "ablation",
    "comparison",
]


def _load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _load_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _decision_zh(decision: str) -> str:
    mapping = {
        "must_read": "必读",
        "worth_reading": "值得看",
        "skip": "可跳过",
        "fetch_pdf": "建议获取PDF",
        "hold": "待观察",
    }
    return mapping.get(decision, decision or "未标注")


def _short_reason(item: dict, mode: str) -> str:
    if mode == "interim":
        return (
            item.get("lite_reasoning", "")
            or item.get("method_summary", "")
            or "暂无说明"
        )[:120]
    return (
        item.get("sharp_commentary", "")
        or item.get("borrowing_value", "")
        or item.get("method_summary", "")
        or "暂无说明"
    )[:160]


def _paper_link(item: dict) -> str:
    return item.get("url", "") or item.get("pdf_url", "") or ""


def _output_path_for_today() -> Path:
    date_str = datetime.now().date().isoformat()
    return daily_papers_dir() / f"{date_str}-论文推荐.md"


def _safe_text(value: str, default: str = "暂无") -> str:
    text = (value or "").strip()
    return text if text else default


def _truncate(text: str, limit: int = 140) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "暂无"
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _note_link(item: dict) -> str:
    links = item.get("note_links", []) or []
    if isinstance(links, list):
        for link in links:
            text = str(link).strip()
            if text:
                return text
    status = str(item.get("note_status", "")).strip().lower()
    if status == "text_note":
        return "文本笔记已生成"
    if status == "note_pending":
        return "note pending"
    return "未回填"


def _figure_manifest_path(item: dict) -> Path | None:
    paper_id = str(item.get("paper_id", "")).strip()
    if not paper_id:
        return None
    return (
        obsidian_vault_path()
        / "assets"
        / "papers"
        / paper_id
        / "figures"
        / "figure_manifest.json"
    )


def _figure_dir(item: dict) -> Path | None:
    manifest_path = _figure_manifest_path(item)
    if manifest_path is None:
        return None
    return manifest_path.parent


def _figure_manifest(item: dict) -> dict:
    manifest_path = _figure_manifest_path(item)
    return _load_object(manifest_path) if manifest_path else {}


def _vault_relpath(path: Path) -> str | None:
    try:
        return path.relative_to(obsidian_vault_path()).as_posix()
    except Exception:
        return None


def _filename_priority(name: str) -> int:
    lowered = name.lower()
    for idx, keyword in enumerate(METHOD_PRIORITY_KEYWORDS):
        if keyword in lowered:
            return 400 - idx * 10
    for idx, keyword in enumerate(RESULT_PRIORITY_KEYWORDS):
        if keyword in lowered:
            return 180 - idx * 10
    return 40


def _role_priority(role: str) -> int:
    mapping = {
        "framework": 500,
        "overview": 490,
        "architecture": 480,
        "pipeline": 470,
        "workflow": 460,
        "method": 450,
        "system": 320,
        "result": 180,
        "supplementary": 20,
        "unknown": 40,
    }
    return mapping.get((role or "unknown").lower(), 40)


def _confidence_priority(label: str) -> int:
    return {"high": 30, "medium": 20, "low": 10}.get((label or "").lower(), 0)


def _choose_manifest_figure(
    figures: list[dict], prefer_results: bool = False
) -> str | None:
    best_path = None
    best_score = -1
    for figure in figures:
        relpath = str(figure.get("vault_relpath", "")).strip()
        if not relpath:
            continue
        role = str(figure.get("estimated_role", "unknown")).lower()
        score = _role_priority(role)
        if prefer_results:
            if role == "result":
                score += 300
            elif role in {"framework", "method"}:
                score -= 200
        else:
            if role == "result":
                score -= 120
        if figure.get("include_in_key_figures"):
            score += 50
        score += _confidence_priority(str(figure.get("extraction_confidence", "")))
        score += _filename_priority(str(figure.get("filename", "")))
        if score > best_score:
            best_score = score
            best_path = relpath
    return best_path


def _resolve_note_figure(item: dict) -> str | None:
    note_ref = _note_link(item)
    if note_ref == "未回填":
        return None
    match = re.search(r"\[\[([^\]]+)\]\]", note_ref)
    if not match:
        return None
    note_name = match.group(1).split("|", 1)[0].strip()
    if not note_name:
        return None
    candidate_paths = list(obsidian_vault_path().rglob(f"{note_name}.md"))
    if not candidate_paths:
        return None
    note_path = candidate_paths[0]
    content = note_path.read_text(encoding="utf-8", errors="ignore")
    key_section = re.search(r"## Figures\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not key_section:
        key_section = re.search(
            r"## 关键图示 \(Key Figures\)\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )
    if not key_section:
        return None
    wiki_links = re.findall(r"!\[\[([^\]]+\.png)\]\]", key_section.group(1))
    for link in wiki_links:
        lowered = link.lower()
        if any(keyword in lowered for keyword in METHOD_PRIORITY_KEYWORDS):
            return link
    return wiki_links[0] if wiki_links else None


def _resolve_thumbnail(item: dict) -> str | None:
    decision = str(item.get("rich_decision", "")).strip().lower()
    if decision != "must_read":
        return None

    manifest = _figure_manifest(item)
    if str(manifest.get("image_mode", "")).lower() == "none":
        return None
    figures = list(manifest.get("figures", [])) if isinstance(manifest, dict) else []
    if figures:
        preferred = _choose_manifest_figure(figures, prefer_results=False)
        if preferred:
            return preferred

    figure_dir = _figure_dir(item)
    if figure_dir and figure_dir.exists():
        files = sorted(figure_dir.glob("*.png"))
        if files:
            ranked = sorted(
                files,
                key=lambda path: _filename_priority(path.name),
                reverse=True,
            )
            relpath = _vault_relpath(ranked[0])
            if relpath and _filename_priority(ranked[0].name) >= 150:
                return relpath

    note_figure = _resolve_note_figure(item)
    if note_figure:
        return note_figure

    if figures:
        return _choose_manifest_figure(figures, prefer_results=True)

    return None


def _image_coverage_summary(item: dict) -> str:
    manifest = _figure_manifest(item)
    if str(manifest.get("image_mode", "")).lower() == "none":
        return "未提取"
    figures = list(manifest.get("figures", [])) if isinstance(manifest, dict) else []
    if figures:
        has_method = any(
            str(fig.get("estimated_role", "")).lower() in {"framework", "method"}
            for fig in figures
        )
        has_result = any(
            str(fig.get("estimated_role", "")).lower() == "result" for fig in figures
        )
        if has_method and has_result:
            return "方法图✓ 结果图✓"
        if has_method:
            return "方法图✓ 结果图-"
        if has_result:
            return "方法图- 结果图✓"
        return "无稳定关键图，详见笔记"

    figure_dir = _figure_dir(item)
    if figure_dir and figure_dir.exists() and any(figure_dir.glob("*.png")):
        names = " ".join(path.name.lower() for path in figure_dir.glob("*.png"))
        has_method = any(keyword in names for keyword in METHOD_PRIORITY_KEYWORDS)
        has_result = any(keyword in names for keyword in RESULT_PRIORITY_KEYWORDS)
        if has_method and has_result:
            return "方法图✓ 结果图△"
        if has_method:
            return "方法图✓ 结果图-"
        if has_result:
            return "方法图- 结果图✓"
    if _note_link(item) != "未回填":
        return "无稳定关键图，详见笔记"
    return "暂无图像信息"


def _core_method(item: dict) -> str:
    return _truncate(item.get("core_method", "") or item.get("method_summary", ""), 150)


def _core_innovation(item: dict) -> str:
    commentary = item.get("sharp_commentary", "") or item.get("method_summary", "")
    innovation = _truncate(commentary, 150)
    if item.get("channel") == "preprint":
        return innovation + "（preprint，结论以当前证据为准）"
    return innovation


def _borrowing_value(item: dict) -> str:
    borrowing = _truncate(
        item.get("borrowing_value", "") or item.get("inspiration_notes", ""), 150
    )
    if item.get("channel") == "published":
        return borrowing + "（优先看可直接复用的模块和评测设计）"
    return borrowing + "（先借鉴方法组件，再核对全文细节）"


def _evidence_boundary(item: dict) -> str | None:
    if item.get("missing_field_report"):
        if item.get("channel") == "preprint":
            return "部分字段缺失，且 preprint 结论仍需结合全文复核"
        return "部分字段缺失，结论受限"
    if item.get("channel") == "preprint":
        return "preprint 阶段，优先关注方法价值与证据强弱"
    return None


def _render_item_card(item: dict, idx: int, mode: str) -> list[str]:
    title = item.get("title", "(untitled)")
    authors = item.get("authors", []) or []
    authors_txt = ", ".join(authors[:6]) if isinstance(authors, list) else str(authors)
    source = item.get("source", "unknown")
    if mode == "interim":
        decision_raw = item.get("lite_decision", "hold")
        decision = _decision_zh(decision_raw)
        confidence = float(item.get("lite_confidence", 0.0))
    else:
        decision_raw = item.get("rich_decision", "worth_reading")
        decision = _decision_zh(decision_raw)
        confidence = float(item.get("rich_confidence", 0.0))
    reason = _short_reason(item, mode)
    link = _paper_link(item)

    lines = [f"### {idx}. {title}", ""]

    thumbnail = _resolve_thumbnail(item) if mode == "final" else None
    if thumbnail:
        lines.append(f"![[{thumbnail}]]")
        lines.append("")

    lines.append(f"- **作者**: {authors_txt if authors_txt else '未知'}")
    lines.append(f"- **来源**: {source}")
    lines.append(f"- **推荐级别**: {decision} (confidence={confidence:.2f})")
    lines.append(f"- **简评**: {reason}")

    if mode == "final" and decision_raw == "must_read":
        lines.append(f"- **核心方法**: {_core_method(item)}")
        lines.append(f"- **核心创新**: {_core_innovation(item)}")
        lines.append(f"- **借鉴意义**: {_borrowing_value(item)}")
        lines.append(f"- **研究笔记**: {_note_link(item)}")
        lines.append(f"- **图像覆盖**: {_image_coverage_summary(item)}")
    elif mode == "final" and decision_raw == "worth_reading":
        lines.append(f"- **核心方法**: {_core_method(item)}")
        lines.append(f"- **借鉴意义**: {_borrowing_value(item)}")

    if link:
        lines.append(f"- **链接**: {link}")
    evidence = _evidence_boundary(item) if mode == "final" else None
    if evidence:
        lines.append(f"- **证据边界**: {evidence}")
    lines.append("")
    return lines


def _render_items(items: list[dict], mode: str) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        lines.extend(_render_item_card(item, idx, mode))
    return lines


def render_interim() -> dict:
    preprint = _load_list(PREPRINT_RICH_PATH)
    published_lite = _load_list(PUBLISHED_LITE_PATH)

    published_waiting = [
        item for item in published_lite if item.get("recommended_for_pdf")
    ][:20]
    preprint_top = preprint[:20]

    lines = [
        "# 每日论文推荐（Interim）",
        "",
        f"- 日期: {datetime.now().date().isoformat()}",
        "- 状态: Published PDF pending",
        "- 说明: 当前页面先交付可用推荐；补充 PDF 后重新运行 daily-papers 即可补全深度分析。",
        "",
        "## Preprint 通道（已完成 rich review）",
        "",
    ]
    lines.extend(_render_items(preprint_top, mode="final"))
    lines.extend(["## Published 通道（待补 PDF）", ""])
    lines.extend(_render_items(published_waiting, mode="interim"))

    output_path = _output_path_for_today()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "mode": "interim",
        "output": str(output_path),
        "counts": {
            "preprint_rich": len(preprint_top),
            "published_lite_waiting_pdf": len(published_waiting),
        },
    }


def render_final() -> dict:
    merged = _load_object(MERGED_PATH)
    rich_pool = merged.get("rich_reviewed_pool", []) if isinstance(merged, dict) else []
    if not isinstance(rich_pool, list):
        rich_pool = []

    published = [item for item in rich_pool if item.get("channel") == "published"]
    preprint = [item for item in rich_pool if item.get("channel") == "preprint"]

    lines = [
        "# 每日论文推荐（Final）",
        "",
        f"- 日期: {datetime.now().date().isoformat()}",
        "- 状态: 推荐已完成",
        "- 说明: 本页面是导航页 + 决策页 + 轻视觉摘要页；只给 must_read 条目展示 1 张缩略关键图。",
        "",
        "## Published 通道（rich）",
        "",
    ]
    lines.extend(_render_items(published, mode="final"))
    lines.extend(["## Preprint 通道（rich）", ""])
    lines.extend(_render_items(preprint, mode="final"))

    output_path = _output_path_for_today()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    must_read_with_thumbnails = sum(
        1
        for item in rich_pool
        if str(item.get("rich_decision", "")).lower() == "must_read"
        and _resolve_thumbnail(item)
    )

    return {
        "status": "ok",
        "mode": "final",
        "output": str(output_path),
        "counts": {
            "published_rich": len(published),
            "preprint_rich": len(preprint),
            "merged_total": len(rich_pool),
            "must_read_with_thumbnails": must_read_with_thumbnails,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["interim", "final"], default="interim")
    args = parser.parse_args()

    payload = render_interim() if args.mode == "interim" else render_final()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
