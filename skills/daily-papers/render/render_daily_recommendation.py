#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
DAILY_PAPERS_DIR = CURRENT_DIR.parent
SHARED_DIR = DAILY_PAPERS_DIR.parent / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from user_config import daily_papers_dir


TMP_DIR = Path("/tmp")
PUBLISHED_LITE_PATH = TMP_DIR / "published_lite_50.json"
PUBLISHED_RICH_PATH = TMP_DIR / "published_review_rich_20.json"
PREPRINT_RICH_PATH = TMP_DIR / "preprint_review_rich_20.json"
MERGED_PATH = TMP_DIR / "daily_review_merged.json"


def _load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


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


def _render_items(items: list[dict], mode: str) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        title = item.get("title", "(untitled)")
        authors = item.get("authors", []) or []
        authors_txt = (
            ", ".join(authors[:6]) if isinstance(authors, list) else str(authors)
        )
        source = item.get("source", "unknown")
        if mode == "interim":
            decision = _decision_zh(item.get("lite_decision", "hold"))
            confidence = float(item.get("lite_confidence", 0.0))
        else:
            decision = _decision_zh(item.get("rich_decision", "worth_reading"))
            confidence = float(item.get("rich_confidence", 0.0))
        reason = _short_reason(item, mode)
        link = _paper_link(item)

        lines.append(f"### {idx}. {title}")
        lines.append(f"- **作者**: {authors_txt if authors_txt else '未知'}")
        lines.append(f"- **来源**: {source}")
        lines.append(f"- **推荐级别**: {decision} (confidence={confidence:.2f})")
        lines.append(f"- **简评**: {reason}")
        if link:
            lines.append(f"- **链接**: {link}")
        if mode == "final" and item.get("missing_field_report"):
            lines.append("- **证据边界**: 部分字段缺失，结论受限")
        lines.append("")
    return lines


def _output_path_for_today() -> Path:
    date_str = datetime.now().date().isoformat()
    return daily_papers_dir() / f"{date_str}-论文推荐.md"


def render_interim() -> dict:
    preprint = _load_list(PREPRINT_RICH_PATH)
    published_lite = _load_list(PUBLISHED_LITE_PATH)

    published_waiting = [
        item for item in published_lite if item.get("recommended_for_pdf")
    ][:20]
    preprint_top = preprint[:20]

    lines = [
        f"# 每日论文推荐（Interim）",
        "",
        f"- 日期: {datetime.now().date().isoformat()}",
        "- 状态: Published 通道等待本地 PDF（Zotero 手动获取中）",
        "- 说明: 当前页面基于 Preprint rich + Published lite 生成，Published 结论仅为 metadata-first 分诊。",
        "",
        "## Preprint 通道（已完成 rich review）",
        "",
    ]
    lines.extend(_render_items(preprint_top, mode="final"))
    lines.extend(
        [
            "## Published 通道（待补 PDF）",
            "",
        ]
    )
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
    merged = {}
    if MERGED_PATH.exists():
        try:
            merged = json.loads(MERGED_PATH.read_text(encoding="utf-8"))
        except Exception:
            merged = {}

    rich_pool = merged.get("rich_reviewed_pool", []) if isinstance(merged, dict) else []
    if not isinstance(rich_pool, list):
        rich_pool = []

    published = [item for item in rich_pool if item.get("channel") == "published"]
    preprint = [item for item in rich_pool if item.get("channel") == "preprint"]

    lines = [
        f"# 每日论文推荐（Final）",
        "",
        f"- 日期: {datetime.now().date().isoformat()}",
        "- 状态: 双通道 rich review 已合并",
        "- 说明: 本页面优先使用 rich review 结果；若字段缺失会显式标注证据边界。",
        "",
        "## Published 通道（rich）",
        "",
    ]
    lines.extend(_render_items(published, mode="final"))
    lines.extend(
        [
            "## Preprint 通道（rich）",
            "",
        ]
    )
    lines.extend(_render_items(preprint, mode="final"))

    output_path = _output_path_for_today()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "mode": "final",
        "output": str(output_path),
        "counts": {
            "published_rich": len(published),
            "preprint_rich": len(preprint),
            "merged_total": len(rich_pool),
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
