#!/usr/bin/env python3
"""Wikipedia revision search with strict temporal cutoff.

Searches Wikipedia and returns article content from the LAST revision BEFORE
the cutoff date. This guarantees zero label leakage — the agent only sees
information that existed before the event resolved.

Usage:
    python tools/wiki_search.py "search query" "2026-01-15"

Args:
    query:  Search terms (e.g., "Golden Knights vs Kings NHL")
    cutoff: Cutoff date in YYYY-MM-DD format. Only revisions before this date
            are returned. This should be the task's resolution date.

The Wikipedia Revision API (rvstart + rvdir=older) returns the exact page
content as it existed just before the cutoff — no future data can leak through.
"""
import sys
import json
import re
import urllib.request
import urllib.parse
import time

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "A-EVOLVE-V2/1.0 (temporal-prediction-benchmark) python-urllib"


def wiki_api(params):
    """Call Wikipedia API with rate limiting."""
    time.sleep(0.15)  # 150ms throttle
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def search_titles(query, limit=5):
    """Search Wikipedia for article titles matching query."""
    try:
        data = wiki_api({
            "action": "query", "list": "search",
            "srsearch": query, "srlimit": limit, "format": "json",
        })
        return [hit["title"] for hit in data.get("query", {}).get("search", [])]
    except Exception as e:
        return []


def get_revision_before(title, cutoff_iso):
    """Fetch article content from the last revision before cutoff.

    Uses rvstart=cutoff + rvdir=older to get the exact page state
    just before the cutoff date.

    Returns (timestamp, plain_text) or None.
    """
    try:
        data = wiki_api({
            "action": "query", "titles": title,
            "prop": "revisions", "rvprop": "content|timestamp",
            "rvlimit": "1", "rvstart": cutoff_iso,
            "rvdir": "older", "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            revs = page.get("revisions", [])
            if not revs:
                return None
            wikitext = revs[0].get("*", "")
            # Convert wikitext to plain text
            text = re.sub(r'\{\{[^}]*\}\}', '', wikitext)  # remove templates
            text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)  # [[link|text]] -> text
            text = re.sub(r"'{2,}", '', text)  # remove bold/italic markup
            text = re.sub(r'<[^>]+>', '', text)  # remove HTML tags
            text = re.sub(r'==+', '', text)  # remove section headers
            text = re.sub(r'\n+', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return (revs[0]["timestamp"][:10], text[:800])
    except Exception:
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/wiki_search.py \"query\" \"2026-01-15\"")
        print("  query:  Search terms")
        print("  cutoff: Date cutoff (YYYY-MM-DD) — only pre-cutoff content returned")
        sys.exit(1)

    query = sys.argv[1]
    cutoff = sys.argv[2]
    cutoff_iso = cutoff + "T23:59:59Z"

    titles = search_titles(query, limit=5)
    if not titles:
        print(f"No Wikipedia articles found for: {query}")
        sys.exit(0)

    results = []
    for title in titles:
        rev = get_revision_before(title, cutoff_iso)
        if rev:
            ts, text = rev
            results.append(f"[Wikipedia rev {ts}] {title}: {text}")
        if len(results) >= 3:
            break

    if results:
        print(f"Results for '{query}' (pre-cutoff, before {cutoff}):\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r}\n")
    else:
        print(f"No pre-cutoff Wikipedia content found for: {query}")
