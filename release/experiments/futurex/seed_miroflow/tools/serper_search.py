#!/usr/bin/env python3
"""Google Search via Serper API with Chinese locale and temporal filtering.

Usage:
    python3 tools/serper_search.py <query> [--gl cn] [--hl zh] [--num 10] [--before DATE]

Temporal constraint:
    If FUTUREX_CUTOFF_DATE is set, results are automatically restricted to
    pages published before that date via Google's tbs parameter + snippet
    heuristic filtering.  This prevents label leakage.

Environment:
    SERPER_API_KEY          — required
    FUTUREX_CUTOFF_DATE     — optional; auto-applied as --before default
"""
import argparse
import json
import os
import re
import sys
import time

import requests

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = os.environ.get("SERPER_BASE_URL", "https://google.serper.dev")
CUTOFF_DATE = os.environ.get("FUTUREX_CUTOFF_DATE", "")

MAX_RETRIES = 3


def _date_to_tbs(before: str) -> str:
    return f"cdr:1,cd_max:{before}"


def _snippet_date_ok(snippet: str, before: str) -> bool:
    dates = re.findall(r'20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}', snippet)
    for d in dates:
        norm = re.sub(r'[年月/]', '-', d).rstrip('-')
        try:
            if norm > before:
                return False
        except Exception:
            pass
    return True


def google_search(q, gl="cn", hl="zh", num=10, before=""):
    if not SERPER_API_KEY:
        return {"error": "SERPER_API_KEY not set"}

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": q, "gl": gl, "hl": hl, "num": num, "autocorrect": False}
    if before:
        payload["tbs"] = _date_to_tbs(before)

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(f"{SERPER_BASE_URL}/search", json=payload,
                                 headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": str(e)}


def format_results(data, before=""):
    lines = []
    if before:
        lines.append(f"[Date filter: results before {before}]\n")

    kg = data.get("knowledgeGraph")
    if kg:
        lines.append(f"[Knowledge Graph] {kg.get('title','')} — {kg.get('description','')}")
        for attr, val in kg.get("attributes", {}).items():
            lines.append(f"  {attr}: {val}")
        lines.append("")

    ab = data.get("answerBox")
    if ab:
        lines.append(f"[Answer Box] {ab.get('title','')} — {ab.get('answer', ab.get('snippet',''))}")
        lines.append("")

    for r in data.get("organic", []):
        snippet = r.get("snippet", "")
        if before and not _snippet_date_ok(snippet, before):
            continue
        lines.append(f"{r.get('position','?')}. {r.get('title','')}")
        lines.append(f"   {snippet}")
        lines.append(f"   URL: {r.get('link','')}")
        lines.append("")

    return "\n".join(lines) if lines else "No results found."


def main():
    parser = argparse.ArgumentParser(description="Google search via Serper")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--gl", default="cn")
    parser.add_argument("--hl", default="zh")
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--before", default=CUTOFF_DATE,
                        help="Only results before this date (YYYY-MM-DD). "
                             "Defaults to FUTUREX_CUTOFF_DATE env var.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    query = " ".join(args.query)
    data = google_search(query, gl=args.gl, hl=args.hl, num=args.num,
                          before=args.before)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_results(data, before=args.before))


if __name__ == "__main__":
    main()
