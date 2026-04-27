#!/usr/bin/env python3
"""Wayback Machine historical snapshot search.

Usage:
    python3 tools/wayback_search.py <url> <YYYY-MM-DD>
    python3 tools/wayback_search.py https://m.douban.com/subject_collection/movie_weekly_best 2026-04-10

Returns the closest archived snapshot URL for the given date.
Adapted from MiroFlow's searching_mcp_server.py.
"""
import argparse
import json
import sys

import requests


def search_wayback(url: str, date: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    timestamp = date.replace("-", "")

    try:
        resp = requests.get(
            "https://archive.org/wayback/available",
            params={"url": url, "timestamp": timestamp},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        snapshots = data.get("archived_snapshots", {})
        closest = snapshots.get("closest")
        if not closest:
            return f"No archived snapshot found for {url} near {date}."

        ts_raw = closest.get("timestamp", "")
        archived_url = closest.get("url", "")
        available = closest.get("available", False)

        if ts_raw and len(ts_raw) >= 8:
            ts_fmt = f"{ts_raw[:4]}-{ts_raw[4:6]}-{ts_raw[6:8]}"
            if len(ts_raw) >= 14:
                ts_fmt += f" {ts_raw[8:10]}:{ts_raw[10:12]}:{ts_raw[12:14]} UTC"
        else:
            ts_fmt = ts_raw

        lines = [
            f"Snapshot found: {available}",
            f"Closest date: {ts_fmt}",
            f"Archived URL: {archived_url}",
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"[ERROR] Wayback search failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Search Wayback Machine")
    parser.add_argument("url", help="URL to look up")
    parser.add_argument("date", help="Target date (YYYY-MM-DD)")
    args = parser.parse_args()

    print(search_wayback(args.url, args.date))


if __name__ == "__main__":
    main()
