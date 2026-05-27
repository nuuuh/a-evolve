#!/usr/bin/env python3
"""Web page reader via Jina Reader API with browser rendering + date check.

Usage:
    python3 tools/jina_reader.py <url> [--max-chars 8000]

Temporal constraint:
    If FUTUREX_CUTOFF_DATE is set, extracts the page's publication date
    via htmldate (if installed) or a regex heuristic and WARNS if the page
    was published after the cutoff.  Content is still returned so the agent
    can decide what to trust.

Environment:
    JINA_API_KEY            — required
    FUTUREX_CUTOFF_DATE     — optional; enables date validation
"""
import argparse
import os
import re

import requests

JINA_API_KEY = os.environ.get("JINA_API_KEY", "")
JINA_BASE_URL = os.environ.get("JINA_BASE_URL", "https://r.jina.ai")
CUTOFF_DATE = os.environ.get("FUTUREX_CUTOFF_DATE", "")


def _extract_date(text, url=""):
    try:
        from htmldate import find_date
        d = find_date(text, url=url, extensive_search=False,
                      original_date=True, outputformat="%Y-%m-%d")
        if d:
            return d
    except ImportError:
        pass
    except Exception:
        pass
    for p in [r'(20\d{2}-\d{2}-\d{2})', r'(20\d{2}年\d{1,2}月\d{1,2}日)',
              r'(20\d{2}/\d{1,2}/\d{1,2})']:
        m = re.search(p, text[:3000])
        if m:
            norm = re.sub(r'[年月/]', '-', m.group(1)).rstrip('日').rstrip('-')
            if len(norm) >= 8:
                return norm
    return None


def read_url(url, max_chars=8000):
    if not JINA_API_KEY:
        return "[ERROR] JINA_API_KEY not set"
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "X-Base": "final",
        "X-Engine": "browser",
        "X-With-Generated-Alt": "true",
        "X-With-Iframe": "true",
        "X-With-Shadow-Dom": "true",
    }
    jina_url = f"{JINA_BASE_URL}/{url}"

    try:
        resp = requests.get(jina_url, headers=headers, timeout=120)
        if resp.status_code == 422:
            return "[ERROR] Jina 422 — URL may point to a file, not a web page."
        resp.raise_for_status()
        content = resp.text

        if "Warning: This page maybe not yet fully loaded" in content:
            resp = requests.get(jina_url, headers=headers, timeout=300)
            resp.raise_for_status()
            content = resp.text

        date_warning = ""
        if CUTOFF_DATE:
            pub = _extract_date(content, url)
            if pub and pub > CUTOFF_DATE:
                date_warning = (
                    f"\n[DATE WARNING: page date {pub} is AFTER cutoff "
                    f"{CUTOFF_DATE}. Data may not have existed at prediction "
                    f"time. Use only pre-cutoff facts from this page.]\n\n"
                )
            elif pub:
                date_warning = f"\n[Page date {pub} — OK (before cutoff {CUTOFF_DATE})]\n\n"

        if max_chars and len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"
        return date_warning + content

    except requests.Timeout:
        return "[ERROR] Jina request timed out (>120s)"
    except Exception as e:
        return f"[ERROR] Jina reader failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Read URL via Jina browser engine")
    parser.add_argument("url")
    parser.add_argument("--max-chars", type=int, default=8000)
    args = parser.parse_args()
    print(read_url(args.url, max_chars=args.max_chars or 0))


if __name__ == "__main__":
    main()
