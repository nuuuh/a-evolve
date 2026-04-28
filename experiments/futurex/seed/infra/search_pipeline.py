#!/usr/bin/env python3
"""Search pipeline for FutureX temporal prediction.

Single-file, no cross-imports, stdlib only. Receives query + cutoff_date
via stdin JSON, returns direct_results + queries via stdout JSON.

Evolution extends this file by adding new source handler functions
and improving the classify() logic.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime


def main():
    raw = sys.stdin.read().strip()
    try:
        ctx = json.loads(raw)
    except json.JSONDecodeError:
        ctx = {"query": raw, "cutoff_date": "2099-01-01"}

    query = ctx.get("query", raw)
    cutoff = ctx.get("cutoff_date", "2099-01-01")

    classification = classify(query)
    direct_results = []

    if classification == "finance":
        direct_results = _finance(query, cutoff)
    elif classification == "news":
        direct_results = _news(query, cutoff)

    queries = _alt_queries(query, classification)

    json.dump({
        "classification": classification,
        "direct_results": direct_results,
        "queries": queries,
    }, sys.stdout)


# ── Classification ──────────────────────────────────────────────

FINANCE_PATTERNS = re.compile(
    r"stock|price|close|closing|share|ticker|index|s&p|nasdaq|dow|"
    r"nyse|etf|bitcoin|crypto|btc|eth|currency|forex|exchange rate|"
    r"commodity|gold|oil|silver",
    re.IGNORECASE,
)

NEWS_PATTERNS = re.compile(
    r"news|announce|event|happen|award|oscar|grammy|election|"
    r"winner|champion|tournament|result|score|match|game",
    re.IGNORECASE,
)


def classify(query):
    if FINANCE_PATTERNS.search(query):
        return "finance"
    if NEWS_PATTERNS.search(query):
        return "news"
    return "general"


# ── Source handlers ─────────────────────────────────────────────

def _finance(query, cutoff):
    """Yahoo Finance v8 chart API — exact OHLCV data."""
    ticker = _extract_ticker(query)
    if not ticker:
        return []
    try:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?range=5d&interval=1d"
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())

        result = data.get("chart", {}).get("result", [])
        if not result:
            return []
        meta = result[0].get("meta", {})
        timestamps = result[0].get("timestamp", [])
        indicators = result[0].get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]
        closes = quotes.get("close", [])

        results = []
        for i, ts in enumerate(timestamps):
            dt = datetime.utcfromtimestamp(ts)
            date_str = dt.strftime("%Y-%m-%d")
            if date_str >= cutoff:
                continue
            if i < len(closes) and closes[i] is not None:
                close = closes[i]
                high = quotes.get("high", [None] * len(timestamps))[i]
                low = quotes.get("low", [None] * len(timestamps))[i]
                vol = quotes.get("volume", [None] * len(timestamps))[i]
                content = f"{meta.get('symbol', ticker)} close on {date_str}: ${close:.2f}"
                if high and low:
                    content += f" (High: ${high:.2f}, Low: ${low:.2f})"
                if vol:
                    content += f" Vol: {vol:,.0f}"
                results.append({
                    "title": f"{meta.get('symbol', ticker)} price {date_str}",
                    "content": content,
                    "source": "Yahoo Finance",
                    "date": date_str,
                })
        return results[-3:]
    except Exception:
        return []


def _extract_ticker(query):
    """Extract stock ticker from natural language query."""
    explicit = re.search(r"\b([A-Z]{1,5})\b", query)
    if explicit and explicit.group(1) not in {
        "THE", "AND", "FOR", "NOT", "BUT", "ARE", "WAS", "HAS", "HAD",
        "HIS", "HER", "WHO", "HOW", "WHY", "YES", "GDP", "FED", "USA",
    }:
        return explicit.group(1)
    tickers = {
        "apple": "AAPL", "google": "GOOGL", "microsoft": "MSFT",
        "amazon": "AMZN", "tesla": "TSLA", "nvidia": "NVDA",
        "meta": "META", "netflix": "NFLX", "bitcoin": "BTC-USD",
        "ethereum": "ETH-USD", "s&p 500": "^GSPC", "s&p": "^GSPC",
        "dow jones": "^DJI", "dow": "^DJI", "nasdaq": "^IXIC",
        "gold": "GC=F", "oil": "CL=F", "silver": "SI=F",
    }
    query_lower = query.lower()
    for name, sym in tickers.items():
        if name in query_lower:
            return sym
    return None


def _news(query, cutoff):
    """Google News RSS — timestamped headlines."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        results = []
        for item in root.iter("item"):
            title = item.findtext("title", "")
            pub_date = item.findtext("pubDate", "")
            link = item.findtext("link", "")
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str >= cutoff:
                        continue
                except ValueError:
                    date_str = ""
            else:
                date_str = ""
            if title:
                results.append({
                    "title": title,
                    "content": f"{title} ({date_str})",
                    "source": "Google News",
                    "date": date_str,
                })
            if len(results) >= 5:
                break
        return results
    except Exception:
        return []


# ── Query expansion ─────────────────────────────────────────────

def _alt_queries(query, classification):
    """Generate alternative search queries based on classification."""
    queries = [query]
    if classification == "finance":
        ticker = _extract_ticker(query)
        if ticker:
            queries.append(f"{ticker} stock price history")
    elif classification == "news":
        queries.append(f"site:wikipedia.org {query}")
    elif classification == "general":
        queries.append(f"{query} Wikipedia")
    return queries[:3]


if __name__ == "__main__":
    main()
