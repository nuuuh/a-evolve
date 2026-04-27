#!/usr/bin/env python3
"""Web page reader via Jina Reader API with browser rendering.

Usage:
    python3 tools/jina_reader.py <url> [--max-chars 8000]

Environment:
    JINA_API_KEY  — required

Adapted from MiroFlow's smart_request.py.  Uses X-Engine: browser to render
JavaScript-heavy pages (Douban, Maoyan, QQ Music, etc.) without login.
"""
import argparse
import os
import sys

import requests

JINA_API_KEY = os.environ.get("JINA_API_KEY", "")
JINA_BASE_URL = os.environ.get("JINA_BASE_URL", "https://r.jina.ai")


def read_url(url: str, max_chars: int = 8000) -> str:
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
            return f"[ERROR] Jina 422 — URL may point to a file, not a web page."
        resp.raise_for_status()
        content = resp.text

        if "Warning: This page maybe not yet fully loaded" in content:
            resp = requests.get(jina_url, headers=headers, timeout=300)
            resp.raise_for_status()
            content = resp.text

        if max_chars and len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"
        return content

    except requests.Timeout:
        return "[ERROR] Jina request timed out (>120s)"
    except Exception as e:
        return f"[ERROR] Jina reader failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Read a URL via Jina browser engine")
    parser.add_argument("url", help="URL to read")
    parser.add_argument("--max-chars", type=int, default=8000,
                        help="Max chars to return (default 8000, 0=unlimited)")
    args = parser.parse_args()

    result = read_url(args.url, max_chars=args.max_chars or 0)
    print(result)


if __name__ == "__main__":
    main()
