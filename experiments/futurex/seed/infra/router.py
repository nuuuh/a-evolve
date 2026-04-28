"""Query classifier and dispatch — entry point for the search pipeline."""


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
    """Classify query by data capability needed."""
    if FINANCE_PATTERNS.search(query):
        return "finance"
    if NEWS_PATTERNS.search(query):
        return "news"
    return "general"


def _alt_queries(query, classification):
    """Generate alternative search queries."""
    queries = [query]
    if classification == "finance":
        queries.append(f"{query} stock price history")
    elif classification == "news":
        queries.append(f"site:wikipedia.org {query}")
    elif classification == "general":
        queries.append(f"{query} Wikipedia")
    return queries[:3]


# Source dispatch table — after bundling, each source's search()
# becomes <module>_search() (e.g. finance_search, news_search).
# Add new entries as new source modules are created.
_SOURCE_DISPATCH = {
    "finance": "finance_search",
    "news": "news_search",
}


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

    # Dispatch to source handler by name
    handler_name = _SOURCE_DISPATCH.get(classification)
    if handler_name:
        handler = globals().get(handler_name)
        if handler:
            try:
                direct_results = handler(query, cutoff)
            except Exception:
                pass

    queries = _alt_queries(query, classification)

    json.dump({
        "classification": classification,
        "direct_results": direct_results,
        "queries": queries,
    }, sys.stdout)


if __name__ == "__main__":
    main()
