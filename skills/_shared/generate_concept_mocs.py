#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from moc_builder import build_tree_mocs
from user_config import concepts_dir, obsidian_vault_path


def main() -> int:
    try:
        vault_root = obsidian_vault_path()
        root_dir = concepts_dir()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Failed to resolve paths: {exc}",
                    "hint": "Check that your configuration has valid obsidian_vault and concepts paths.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    if not vault_root.exists():
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Obsidian vault directory does not exist: {vault_root}",
                    "hint": "Ensure the vault path is correct in your configuration.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    try:
        root_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Cannot create concepts directory: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    try:
        summary = build_tree_mocs(
            vault_root=vault_root,
            root_dir=root_dir,
            title_prefix="概念目录页",
            intro="用于浏览概念笔记和对应分类入口。",
        )
        result = summary.to_dict()
        result["status"] = "ok"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc()[:500],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
