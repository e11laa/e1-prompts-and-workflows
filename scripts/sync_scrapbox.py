#!/usr/bin/env python3
"""Sync all public Scrapbox pages from project 'ellimissinina' into docs/scrapbox/pages/."""

import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PROJECT = "ellimissinina"
API_BASE = f"https://scrapbox.io/api/pages/{PROJECT}"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "scrapbox", "pages")
README_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "scrapbox", "README.md")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Text conversion helpers
# ---------------------------------------------------------------------------

def _bracket_link_to_md(text: str) -> str:
    """Convert Scrapbox bracket notation to plain text or 'name (url)' form."""
    def replace(m: re.Match) -> str:
        inner = m.group(1).strip()
        # Detect '[name... url]' where url is the last whitespace-delimited token
        parts = inner.rsplit(None, 1)
        if len(parts) == 2:
            name, url = parts
            if url.startswith("http://") or url.startswith("https://"):
                return f"{name} ({url})"
        # Detect '[url name...]' (url first)
        parts_fwd = inner.split(None, 1)
        if len(parts_fwd) == 2:
            url, name = parts_fwd
            if url.startswith("http://") or url.startswith("https://"):
                return f"{name} ({url})"
        # Plain bracket: '[foo]' -> 'foo'
        return inner
    return re.sub(r"\[([^\[\]]+)\]", replace, text)


def _bare_md_links(text: str) -> str:
    """Convert [url](url) where label == url to bare url."""
    def replace(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        if label == url:
            return url
        return m.group(0)
    return re.sub(r"\[([^\[\]]+)\]\(([^)]+)\)", replace, text)


def _convert_line(line: str) -> str:
    """Convert a single Scrapbox line to Markdown."""
    line = _bracket_link_to_md(line)
    line = _bare_md_links(line)
    return line


def scrapbox_lines_to_markdown(lines: list) -> str:
    """Convert list of Scrapbox line objects to Markdown body text."""
    result = []
    in_code = False
    code_lang = ""

    for line_obj in lines:
        text = line_obj.get("text", "") if isinstance(line_obj, dict) else str(line_obj)

        # Detect code block start: 'code:filename' or 'code:lang'
        if not in_code:
            code_match = re.match(r"^code:(.+)$", text.strip())
            if code_match:
                code_lang = code_match.group(1).strip()
                result.append(f"```{code_lang}")
                in_code = True
                continue

        if in_code:
            # Code blocks in Scrapbox are indented lines following the code: line
            if text.startswith("\t") or text.startswith(" "):
                result.append(text.lstrip("\t "))
            else:
                result.append("```")
                in_code = False
                result.append(_convert_line(text))
            continue

        result.append(_convert_line(text))

    if in_code:
        result.append("```")

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Create a filesystem-safe ASCII slug from a title."""
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Lowercase
    text = text.lower()
    # Replace spaces and common separators with hyphen
    text = re.sub(r"[\s/\\:]+", "-", text)
    # Remove characters that are not ASCII alphanumeric or hyphen/underscore
    text = re.sub(r"[^\x00-\x7f]", "", text)
    text = re.sub(r"[^a-z0-9\-_]", "", text)
    # Collapse repeated hyphens
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")
    # Truncate
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "page"


def safe_filename(title: str, page_id: str, used: set) -> str:
    """Return a unique filename (without .md) for the given page."""
    slug = slugify(title)
    if slug not in used:
        return slug
    # Collision: append page_id suffix
    candidate = f"{slug}-{page_id}"
    return candidate


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "scrapbox-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_page_list() -> list:
    """Fetch all pages from the project (handles pagination)."""
    pages = []
    skip = 0
    limit = 100
    while True:
        url = f"{API_BASE}?skip={skip}&limit={limit}"
        data = fetch_json(url)
        batch = data.get("pages", [])
        pages.extend(batch)
        if len(batch) < limit:
            break
        skip += len(batch)
    return pages


def fetch_page(title: str) -> dict:
    encoded = urllib.parse.quote(title, safe="")
    url = f"{API_BASE}/{encoded}"
    return fetch_json(url)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Fetching page list for project '{PROJECT}'...")
    page_list = fetch_page_list()
    print(f"  Found {len(page_list)} pages.")

    used_slugs: set = set()
    generated_files: list = []

    for page_meta in page_list:
        title = page_meta.get("title", "")
        page_id = page_meta.get("id", "")
        if not title:
            continue

        print(f"  Fetching: {title}")
        try:
            page_data = fetch_page(title)
        except Exception as exc:
            print(f"    ERROR fetching '{title}': {exc}")
            continue

        lines = page_data.get("lines", [])
        # First line is typically the title itself; skip it
        body_lines = lines[1:] if lines else []
        body_md = scrapbox_lines_to_markdown(body_lines)

        scrapbox_url = f"https://scrapbox.io/{PROJECT}/{urllib.parse.quote(title, safe='')}"

        filename = safe_filename(title, page_id, used_slugs)
        used_slugs.add(filename)

        content = f"# {title}\n\nSource: {scrapbox_url}\n\n最終同期日: {TODAY}\n\n{body_md}\n"

        out_path = os.path.join(OUTPUT_DIR, f"{filename}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        generated_files.append((title, filename))
        print(f"    Wrote: {out_path}")

    # Remove stale files no longer in Scrapbox
    current_files = {f"{fn}.md" for _, fn in generated_files}
    for existing in os.listdir(OUTPUT_DIR):
        if existing.endswith(".md") and existing != "README.md" and existing not in current_files:
            os.remove(os.path.join(OUTPUT_DIR, existing))
            print(f"  Removed stale file: {existing}")

    # Update README sync date
    _update_readme_sync_date(TODAY, generated_files)
    print("Done.")


def _update_readme_sync_date(date_str: str, pages: list) -> None:
    """Update the last sync date in docs/scrapbox/README.md."""
    if not os.path.exists(README_PATH):
        return
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    # Replace the last sync date line
    updated = re.sub(
        r"最終同期日[:：]\s*\d{4}-\d{2}-\d{2}",
        f"最終同期日: {date_str}",
        content,
    )
    if updated == content and "最終同期日" not in content:
        # Append if not present
        updated = content.rstrip() + f"\n\n最終同期日: {date_str}\n"
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)


if __name__ == "__main__":
    main()
