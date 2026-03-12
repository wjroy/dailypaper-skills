#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
SKILL_DIR = CURRENT_DIR.parent
SHARED_DIR = SKILL_DIR.parent / "_shared"


def _run(script_path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or "").strip()
        try:
            payload: dict[str, Any] = json.loads(output) if output else {}
        except Exception:
            payload = {"raw_output": output}
        payload["returncode"] = proc.returncode
        if proc.returncode != 0 and proc.stderr:
            payload["stderr_summary"] = proc.stderr.strip()[:500]
        return payload
    except Exception as exc:
        return {"returncode": -1, "error": str(exc)}


def run() -> dict[str, Any]:
    concept = _run(SHARED_DIR / "generate_concept_mocs.py")
    paper = _run(SHARED_DIR / "generate_paper_mocs.py")

    completed = []
    failed = []
    for label, payload in [("concept", concept), ("paper", paper)]:
        if payload.get("returncode") == 0:
            completed.append(label)
        else:
            failed.append(label)

    if completed and failed:
        status = "partial"
    elif completed:
        status = "ok"
    else:
        status = "failed"

    return {
        "status": status,
        "message": "MOCs refreshed",
        "completed": completed,
        "failed": failed,
        "details": {
            "concept": concept,
            "paper": paper,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
