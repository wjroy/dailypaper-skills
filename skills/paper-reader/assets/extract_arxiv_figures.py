#!/usr/bin/env python3
"""Extract figures (images + captions) from arXiv HTML pages.

Usage:
    python extract_arxiv_figures.py <arxiv_id_or_url>
    python extract_arxiv_figures.py 2501.12345
    python extract_arxiv_figures.py https://arxiv.org/abs/2501.12345

Output: JSON array of figure records to stdout. Example:
    [
      {
        "figure_id": "Figure 1",
        "caption": "Overview of our method ...",
        "image_urls": ["https://arxiv.org/html/2501.12345v1/x1.png"],
        "source": "arxiv_html"
      },
      ...
    ]

Exit codes:
    0 — success (figures extracted)
    1 — no figures found / HTML unavailable
    2 — usage error
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any


# ---------------------------------------------------------------------------
# arXiv ID / URL normalisation
# ---------------------------------------------------------------------------

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


def normalise_arxiv_id(raw: str) -> str | None:
    """Extract bare arXiv ID (with optional version) from a URL or ID string."""
    m = _ARXIV_ID_RE.search(raw)
    if not m:
        return None
    return m.group(0)


def arxiv_html_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/html/{arxiv_id}"


# ---------------------------------------------------------------------------
# Lightweight HTML parser (stdlib only — no bs4 / lxml dependency)
# ---------------------------------------------------------------------------


class _FigureExtractor(HTMLParser):
    """Single-pass HTML parser that collects <figure> blocks.

    For each <figure> it records:
    - all <img> src attributes (→ image URLs)
    - text inside <figcaption> (→ caption)
    - the figure's id attribute if present
    """

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.figures: list[dict[str, Any]] = []

        # state
        self._in_figure = False
        self._in_figcaption = False
        self._current_imgs: list[str] = []
        self._current_caption_parts: list[str] = []
        self._current_id = ""
        self._figure_depth = 0  # nesting depth for <figure>

    # -- helpers --------------------------------------------------------

    def _resolve_url(self, src: str) -> str:
        """Resolve relative img src to absolute URL, with dedup guard."""
        if src.startswith(("http://", "https://")):
            url = src
        elif src.startswith("/"):
            url = f"https://arxiv.org{src}"
        else:
            url = f"{self.base_url}/{src}"
        # Dedup guard: remove doubled arxiv_id path segments
        url = _dedup_arxiv_path(url)
        return url

    # -- parser callbacks -----------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)

        if tag == "figure":
            if not self._in_figure:
                self._in_figure = True
                self._figure_depth = 1
                self._current_imgs = []
                self._current_caption_parts = []
                self._current_id = attr_dict.get("id") or ""
            else:
                self._figure_depth += 1
            return

        if self._in_figure:
            if tag == "img":
                src = attr_dict.get("src", "")
                if src:
                    self._current_imgs.append(self._resolve_url(src))
            elif tag == "figcaption":
                self._in_figcaption = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "figure" and self._in_figure:
            self._figure_depth -= 1
            if self._figure_depth <= 0:
                self._flush_figure()
                self._in_figure = False
        elif tag == "figcaption":
            self._in_figcaption = False

    def handle_data(self, data: str) -> None:
        if self._in_figcaption:
            self._current_caption_parts.append(data)

    # -- flush ----------------------------------------------------------

    def _flush_figure(self) -> None:
        caption = " ".join("".join(self._current_caption_parts).split())
        # Skip non-content figures (e.g. icon-only elements with no caption
        # and no meaningful images).
        if not self._current_imgs and not caption:
            return
        # Filter out tiny icon images (ar5iv uses /x*.png naming; icons tend
        # to have very short filenames or special patterns, but we can't know
        # size without fetching.  We keep all and let downstream filter.)
        figure_id = _extract_figure_label(caption, self._current_id)
        self.figures.append(
            {
                "figure_id": figure_id,
                "caption": caption,
                "image_urls": list(self._current_imgs),
                "source": "arxiv_html",
            }
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIGURE_LABEL_RE = re.compile(
    r"(?:Figure|Fig\.?|Table|Algorithm)\s*\.?\s*(\d+)",
    re.IGNORECASE,
)


def _extract_figure_label(caption: str, html_id: str) -> str:
    """Derive a human-readable label like 'Figure 1' from caption or id."""
    m = _FIGURE_LABEL_RE.search(caption)
    if m:
        prefix = m.group(0).split()[0].rstrip(".")
        num = m.group(1)
        # Normalise prefix
        if prefix.lower().startswith("fig"):
            prefix = "Figure"
        elif prefix.lower().startswith("tab"):
            prefix = "Table"
        elif prefix.lower().startswith("alg"):
            prefix = "Algorithm"
        return f"{prefix} {num}"
    # Fallback: use HTML element id (e.g. "S3.F2" → "Figure 2")
    id_m = re.search(r"F(\d+)", html_id)
    if id_m:
        return f"Figure {id_m.group(1)}"
    return ""


_DEDUP_RE = re.compile(r"(\d{4}\.\d{4,5}v?\d*)/\1")


def _dedup_arxiv_path(url: str) -> str:
    """Remove doubled arxiv-id segments from URL path."""
    while _DEDUP_RE.search(url):
        url = _DEDUP_RE.sub(r"\1", url)
    return url


# ---------------------------------------------------------------------------
# Fetch + extract pipeline
# ---------------------------------------------------------------------------


def fetch_html(url: str, timeout: int = 30) -> str | None:
    """Fetch HTML from *url*; return None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def extract_figures_from_html(html: str, base_url: str) -> list[dict[str, Any]]:
    """Parse *html* and return a list of figure records."""
    parser = _FigureExtractor(base_url)
    parser.feed(html)
    return parser.figures


def extract_figures(arxiv_id: str) -> list[dict[str, Any]]:
    """End-to-end: fetch arXiv HTML and extract all figures.

    Returns a list of figure dicts or an empty list on failure.
    """
    url = arxiv_html_url(arxiv_id)
    html = fetch_html(url)
    if html is None:
        # Try without version suffix
        bare = arxiv_id.split("v")[0]
        if bare != arxiv_id:
            url = arxiv_html_url(bare)
            html = fetch_html(url)
    if html is None:
        return []
    return extract_figures_from_html(html, url)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python extract_arxiv_figures.py <arxiv_id_or_url>", file=sys.stderr
        )
        sys.exit(2)

    raw = sys.argv[1]
    arxiv_id = normalise_arxiv_id(raw)
    if not arxiv_id:
        print(f"Could not parse arXiv ID from: {raw}", file=sys.stderr)
        sys.exit(2)

    figures = extract_figures(arxiv_id)
    if not figures:
        print(
            f"No figures extracted for {arxiv_id} (HTML may be unavailable).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Use ensure_ascii=True for safe Windows terminal output; downstream
    # consumers (json.loads) handle Unicode escapes transparently.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    json.dump(figures, sys.stdout, ensure_ascii=False, indent=2)
    print()  # trailing newline
    # Summary to stderr
    n_figs = sum(1 for f in figures if f["figure_id"].startswith("Figure"))
    n_tabs = sum(1 for f in figures if f["figure_id"].startswith("Table"))
    n_other = len(figures) - n_figs - n_tabs
    print(
        f"Extracted {len(figures)} elements: {n_figs} figures, {n_tabs} tables, {n_other} other",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
