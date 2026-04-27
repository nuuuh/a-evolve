#!/usr/bin/env python3
"""Google Search via Serper API with Chinese locale support.

Usage:
    python3 tools/serper_search.py <query> [--gl cn] [--hl zh] [--num 10]

Environment:
    SERPER_API_KEY  — required

Adapted from MiroFlow's searching_mcp_server.py.
"""
import argparse
import json
import os
import sys
import time

import requests

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = os.environ.get("SERPER_BASE_URL", "https://google.serper.dev")

MAX_RETRIES = 3


def google_search(q: str, gl: str = "cn", hl: str = "zh", num: int = 10,
                   tbs: str | None = None) -> dict:
    if not SERPER_API_KEY:
        return {"error": "SERPER_API_KEY not set"}

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload: dict = {
        "q": q,
        "gl": gl,
        "hl": hl,
        "num": num,
        "autocorrect": False,
    }
    if tbs:
        payload["tbs"] = tbs

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                f"{SERPER_BASE_URL}/search",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": str(e)}


def format_results(data: dict) -> str:
    lines = []

    kg = data.get("knowledgeGraph")
    if kg:
        lines.append(f"[Knowledge Graph] {kg.get('title', '')} — {kg.get('description', '')}")
        for attr, val in kg.get("attributes", {}).items():
            lines.append(f"  {attr}: {val}")
        lines.append("")

    ab = data.get("answerBox")
    if ab:
        lines.append(f"[Answer Box] {ab.get('title', '')} — {ab.get('answer', ab.get('snippet', ''))}")
        lines.append("")

    for r in data.get("organic", []):
        pos = r.get("position", "?")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        lines.append(f"{pos}. {title}")
        lines.append(f"   {snippet}")
        lines.append(f"   URL: {link}")
        lines.append("")

    return "\n".join(lines) if lines else "No results found."


def main():
    parser = argparse.ArgumentParser(description="Google search via Serper")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--gl", default="cn", help="Country code (default: cn)")
    parser.add_argument("--hl", default="zh", help="Language (default: zh)")
    parser.add_argument("--num", type=int, default=10, help="Number of results")
    parser.add_argument("--tbs", default=None, help="Time-based search filter")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    query = " ".join(args.query)
    data = google_search(query, gl=args.gl, hl=args.hl, num=args.num, tbs=args.tbs)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_results(data))


if __name__ == "__main__":
    main()
