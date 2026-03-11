#!/usr/bin/env python3
"""Selectively download unreachable images in Obsidian markdown notes.

Usage:
    python3 download_note_images.py <note.md>

For each external image link ![...](https://...):
  - Reachable (HTTP 200 within 10s) → keep as-is
  - Unreachable → download to assets/ and replace with Obsidian wikilink
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

CURL_TIMEOUT = 10
CONCURRENCY = 5
DEVNULL_PATH = os.devnull


def parse_note(text: str) -> list[dict]:
    """Extract all external image references with their positions.

    Returns list of dicts: {full_match, alt, url, start, end}
    """
    pattern = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")
    images = []
    for m in pattern.finditer(text):
        images.append(
            {
                "full_match": m.group(0),
                "alt": m.group(1),
                "url": m.group(2),
                "start": m.start(),
                "end": m.end(),
            }
        )
    return images


def get_method_name(note_path: Path) -> str:
    """Extract method name from note filename (stem)."""
    return note_path.stem


def extract_arxiv_id(url: str) -> str:
    """Try to extract arxiv_id from a URL."""
    m = re.search(r"(\d{4}\.\d{4,5})", url)
    return m.group(1) if m else ""


def extract_local_pdf_paths(note_text: str, note_path: Path) -> list[Path]:
    """Extract local PDF paths from note frontmatter/body hints.

    Supported keys/hints (best effort):
    - pdf_path: /abs/path/file.pdf
    - pdf: /abs/path/file.pdf
    - local_pdf_paths: ["...", "..."]
    - any explicit *.pdf absolute path in note text
    """
    candidates: list[Path] = []

    # Key-value style lines
    key_patterns = [
        r"(?im)^\s*pdf_path\s*:\s*(.+?)\s*$",
        r"(?im)^\s*pdf\s*:\s*(.+?)\s*$",
        r"(?im)^\s*local_pdf\s*:\s*(.+?)\s*$",
    ]
    for pat in key_patterns:
        for value in re.findall(pat, note_text):
            raw = value.strip().strip('"').strip("'")
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = (note_path.parent / p).resolve()
            candidates.append(p)

    # JSON-like list inline
    m = re.search(r"(?is)local_pdf_paths\s*:\s*\[(.*?)\]", note_text)
    if m:
        inner = m.group(1)
        for token in re.findall(
            r'"([^"]+\.pdf)"|\'([^\']+\.pdf)\'|([^,\]\s]+\.pdf)', inner
        ):
            val = next((x for x in token if x), "").strip()
            if not val:
                continue
            p = Path(val).expanduser()
            if not p.is_absolute():
                p = (note_path.parent / p).resolve()
            candidates.append(p)

    # Absolute path hints ending in .pdf
    for raw in re.findall(r"([A-Za-z]:\\[^\n\r]+?\.pdf|/[^\s\)\]]+\.pdf)", note_text):
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (note_path.parent / p).resolve()
        candidates.append(p)

    # Dedup + exists
    out = []
    seen = set()
    for p in candidates:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.exists() and p.is_file():
            out.append(p)
    return out


async def check_url(url: str, sem: asyncio.Semaphore) -> bool:
    """Check if a URL is reachable (HTTP 200) using curl."""
    async with sem:
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "-sL",
                "-o",
                DEVNULL_PATH,
                "-w",
                "%{http_code}",
                "--max-time",
                str(CURL_TIMEOUT),
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=CURL_TIMEOUT + 5
            )
            code = stdout.decode().strip() if stdout else ""
            return code == "200"
        except (asyncio.TimeoutError, Exception):
            return False


async def download_image(url: str, dest: Path, sem: asyncio.Semaphore) -> bool:
    """Download an image from URL to dest path. Returns True on success."""
    async with sem:
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "-sL",
                "--max-time",
                str(CURL_TIMEOUT + 10),
                "-o",
                str(dest),
                url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=CURL_TIMEOUT + 15)
            # Verify file exists and is non-trivial
            return dest.exists() and dest.stat().st_size > 1024
        except (asyncio.TimeoutError, Exception):
            return False


async def try_pdf_extract(
    arxiv_id: str,
    assets_dir: Path,
    method_name: str,
    fig_num: int,
    sem: asyncio.Semaphore,
    local_pdf_candidates: list[Path] | None = None,
) -> Path | None:
    """Try to extract a figure from local PDF first, then arXiv PDF fallback."""
    local_pdf_candidates = local_pdf_candidates or []
    pdf_candidate_paths = list(local_pdf_candidates)

    if not pdf_candidate_paths and arxiv_id:
        pdf_candidate_paths.append(Path(f"/tmp/arxiv_{arxiv_id}.pdf"))

    if not pdf_candidate_paths:
        return None
    async with sem:
        try:
            prefix = str(assets_dir / f"{method_name}_pdf_fig")

            # If only arXiv temp path is present and file is missing, download it.
            if (
                len(pdf_candidate_paths) == 1
                and str(pdf_candidate_paths[0]).startswith("/tmp/arxiv_")
                and not pdf_candidate_paths[0].exists()
                and arxiv_id
            ):
                proc = await asyncio.create_subprocess_exec(
                    "curl",
                    "-sL",
                    "--max-time",
                    "30",
                    "-o",
                    str(pdf_candidate_paths[0]),
                    f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.communicate(), timeout=35)

            # Extract from first available PDF.
            for pdf_path in pdf_candidate_paths:
                if not pdf_path.exists():
                    continue
                proc = await asyncio.create_subprocess_exec(
                    "pdfimages",
                    "-png",
                    str(pdf_path),
                    prefix,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.communicate(), timeout=30)
                # Find extracted images > 10KB
                extracted = sorted(assets_dir.glob(f"{method_name}_pdf_fig-*.png"))
                large = [f for f in extracted if f.stat().st_size > 10240]
                if fig_num - 1 < len(large):
                    return large[fig_num - 1]
        except (asyncio.TimeoutError, Exception):
            pass
    return None


def update_frontmatter(text: str) -> str:
    """Update image_source from 'online' to 'mixed' in frontmatter."""
    return re.sub(
        r"^(image_source:\s*)online\s*$",
        r"\1mixed",
        text,
        count=1,
        flags=re.MULTILINE,
    )


async def process_note(note_path: Path) -> dict:
    """Main processing logic. Returns summary dict."""
    text = note_path.read_text(encoding="utf-8")
    images = parse_note(text)

    if not images:
        print(f"No external images found in {note_path.name}")
        return {"total": 0, "reachable": 0, "localized": 0, "failed": 0}

    method_name = get_method_name(note_path)
    local_pdf_candidates = extract_local_pdf_paths(text, note_path)
    assets_dir = note_path.parent / "assets"
    sem = asyncio.Semaphore(CONCURRENCY)

    print(f"Found {len(images)} external image(s) in {note_path.name}")

    # Step 1: Check reachability concurrently
    check_tasks = [check_url(img["url"], sem) for img in images]
    reachable = await asyncio.gather(*check_tasks)

    # Step 2: Process unreachable images
    replacements = {}  # full_match -> new_reference
    localized = 0
    failed = 0

    for i, (img, is_ok) in enumerate(zip(images, reachable)):
        if is_ok:
            print(f"  [OK] {img['url'][:80]}")
            continue

        fig_num = i + 1
        ext = Path(img["url"]).suffix or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
            ext = ".png"
        local_name = f"{method_name}_fig{fig_num}{ext}"
        local_path = assets_dir / local_name

        # Ensure assets dir exists
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Try direct download first
        print(f"  [DL] {img['url'][:80]}")
        ok = await download_image(img["url"], local_path, sem)

        # Fallback: try PDF extraction
        if not ok:
            arxiv_id = extract_arxiv_id(img["url"])
            if arxiv_id:
                print(f"  [PDF fallback] arxiv:{arxiv_id} fig{fig_num}")
                pdf_path = await try_pdf_extract(
                    arxiv_id,
                    assets_dir,
                    method_name,
                    fig_num,
                    sem,
                    local_pdf_candidates=local_pdf_candidates,
                )
                if pdf_path:
                    # Rename to our convention
                    pdf_path.rename(local_path)
                    ok = True
            elif local_pdf_candidates:
                pdf_path = await try_pdf_extract(
                    "",
                    assets_dir,
                    method_name,
                    fig_num,
                    sem,
                    local_pdf_candidates=local_pdf_candidates,
                )
                if pdf_path:
                    pdf_path.rename(local_path)
                    ok = True

        if ok and local_path.exists() and local_path.stat().st_size > 1024:
            new_ref = f"![[{local_name}|600]]"
            replacements[img["full_match"]] = new_ref
            localized += 1
            print(f"  [OK] Localized → {local_name}")
        else:
            failed += 1
            # Clean up partial download
            if local_path.exists():
                local_path.unlink()
            print(f"  [FAIL] Could not download {img['url'][:80]}")

    # Step 3: Apply replacements to text
    if replacements:
        new_text = text
        for old, new in replacements.items():
            new_text = new_text.replace(old, new)
        new_text = update_frontmatter(new_text)
        note_path.write_text(new_text, encoding="utf-8")
        print(f"Updated {note_path.name}: {localized} image(s) localized")

    total = len(images)
    reachable_count = sum(1 for r in reachable if r)
    return {
        "total": total,
        "reachable": reachable_count,
        "localized": localized,
        "failed": failed,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 download_note_images.py <note.md>", file=sys.stderr)
        sys.exit(1)

    note_path = Path(sys.argv[1]).expanduser().resolve()
    if not note_path.exists():
        print(f"File not found: {note_path}", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(process_note(note_path))

    print(
        f"\nSummary: {result['total']} images — "
        f"{result['reachable']} reachable, "
        f"{result['localized']} localized, "
        f"{result['failed']} failed"
    )

    # Output JSON for programmatic use
    print(json.dumps(result), file=sys.stderr)


if __name__ == "__main__":
    main()
