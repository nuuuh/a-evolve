#!/usr/bin/env python3
"""Wikipedia Revision API — fetch page revisions for a given month.

Usage:
    python3 tools/wiki_revision.py <page_title> <YYYY-MM> [--lang en] [--limit 20]

Returns revision IDs and timestamps.  Use the revision URL to read
the page content as it was on that date (zero-leakage by construction).

Adapted from MiroFlow's searching_mcp_server.py.
"""
import argparse
import calendar
import json
import sys

import requests


def search_revisions(title: str, year: int, month: int,
                     lang: str = "en", limit: int = 20) -> str:
    last_day = calendar.monthrange(year, month)[1]

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvlimit": min(limit, 500),
        "rvstart": f"{year}-{month:02d}-{last_day}T23:59:59Z",
        "rvend": f"{year}-{month:02d}-01T00:00:00Z",
        "rvdir": "newer",
        "rvprop": "timestamp|ids",
    }

    base = f"https://{lang}.wikipedia.org/w/api.php"

    try:
        resp = requests.get(base, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] Wikipedia API failed: {e}"

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return "No results from Wikipedia API."

    page_id = list(pages.keys())[0]
    if page_id == "-1":
        return f"Page '{title}' not found on {lang}.wikipedia.org."

    revisions = pages[page_id].get("revisions", [])
    if not revisions:
        return f"No revisions found for '{title}' in {year}-{month:02d}."

    lines = [f"Revisions for '{title}' ({year}-{month:02d}): {len(revisions)} found\n"]
    for rev in revisions[:limit]:
        rid = rev["revid"]
        ts = rev["timestamp"]
        url = f"https://{lang}.wikipedia.org/w/index.php?title={title}&oldid={rid}"
        lines.append(f"  {ts}  revid={rid}")
        lines.append(f"    {url}")

    lines.append(f"\nTo read a specific revision, use jina_reader.py with the revision URL.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Wikipedia revision search")
    parser.add_argument("title", help="Wikipedia page title")
    parser.add_argument("month", help="Target month (YYYY-MM)")
    parser.add_argument("--lang", default="en", help="Wiki language (default: en)")
    parser.add_argument("--limit", type=int, default=20, help="Max revisions")
    args = parser.parse_args()

    parts = args.month.split("-")
    year, month = int(parts[0]), int(parts[1])
    print(search_revisions(args.title, year, month, lang=args.lang, limit=args.limit))


if __name__ == "__main__":
    main()
