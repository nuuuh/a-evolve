PIPELINE CONTRACT:

The framework bundles infra/sources/*.py + utils.py + router.py into
a single search_pipeline.py that the solver runs as a subprocess.

Input (JSON via stdin to the bundled pipeline):
  {{"query": "...", "cutoff_date": "YYYY-MM-DD"}}

Output (JSON via stdout):
  {{"classification": "...", "direct_results": [...], "queries": [...]}}

  direct_results: structured API data (pre-verified dates)
    [{{"title": str, "content": str, "source": str, "date": str}}]
  queries: alternative search terms for the framework's web search

ARCHITECTURE:
  infra/
    sources/
      finance.py       — stock prices, indices, crypto, forex
      sports.py        — match results, scores, standings
      news.py          — dated headlines from RSS/news APIs
      climate.py       — weather, temperature, environmental data
      election.py      — election results, polling data
      ...              — add more as needed
    utils.py           — shared: _fetch(), _fetch_json(), date helpers
    router.py          — classify(query) + main() entry point

EACH SOURCE MODULE pattern:
  def search(query, cutoff):
      results = []
      # Try primary API
      # Try fallback API
      # Return list of {{"title", "content", "source", "date"}} dicts
      return results

EVOLUTION IS INCREMENTAL:
- Add new source files for new data capabilities
- Improve existing sources by adding fallback API chains
- Improve router.py classify() to handle more query types
- Add shared helpers to utils.py

SOURCE CATEGORIES TO CONSIDER:
- Structured data APIs (financial, weather, sports — exact values)
- News aggregators with date filtering (RSS feeds, archive APIs)
- AI search APIs (Serper, Jina, Tavily, Exa — if API keys available)
- Wikipedia/Wikidata APIs (structured knowledge, historical revisions)
- Government/institutional APIs (FRED, census, election data)

OUTPUT QUALITY IS CRITICAL:
- "AAPL close on 2026-01-07: $237.42" → solver gets answer in one read
- Raw HTML or "various results suggest..." → useless, wastes solver turns
- Cap each direct_result content at 500 chars
- Lead with the key fact, include source attribution and date
