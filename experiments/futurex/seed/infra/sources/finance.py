"""Finance source — stock prices, indices, crypto, forex."""


def search(query, cutoff):
    """Yahoo Finance v8 chart API — exact OHLCV data."""
    ticker = _extract_ticker(query)
    if not ticker:
        return []
    try:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?range=5d&interval=1d"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
