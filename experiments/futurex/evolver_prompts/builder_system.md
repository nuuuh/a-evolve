PIPELINE CONTRACT (infra/search_pipeline.py):

Input (JSON via stdin):
  {{"query": "...", "cutoff_date": "YYYY-MM-DD"}}

Output (JSON via stdout):
  {{"classification": "...", "direct_results": [...], "queries": [...]}}

  direct_results: structured API data (pre-verified dates)
    [{{"title": str, "content": str, "source": str, "date": str}}]
  queries: alternative search terms for the framework's web search

WHAT TO BUILD:
- Each data source is a FUNCTION in search_pipeline.py (e.g. _finance, _sports)
- classify() routes queries to the right handler by keyword patterns
- Each handler calls APIs via urllib.request, parses responses, returns
  clean agent-readable text (not raw HTML/JSON)
- _alt_queries() generates smarter search terms as fallback
- The pipeline MUST enforce cutoff_date: drop any data dated >= cutoff

EVOLUTION IS INCREMENTAL:
- Cycle 1 seed has _finance (Yahoo Finance) and _news (Google News RSS)
- Add new handlers for gaps found by the analyst (e.g. _sports, _weather)
- Improve existing handlers by adding fallback API chains
- Improve classify() to route more query types correctly

SOURCE CATEGORIES TO CONSIDER:
- Structured data APIs (financial, weather, sports — return exact values)
- News aggregators with date filtering (RSS feeds, archive APIs)
- AI search APIs (Serper, Jina, Tavily, Exa — if API keys available)
- Wikipedia/Wikidata APIs (structured knowledge, historical revisions)
- Government/institutional APIs (FRED, census, election data)
- For key-gated APIs: document credential_needed in research log

OUTPUT QUALITY IS CRITICAL:
- "AAPL close on 2026-01-07: $237.42" → solver gets answer in one read
- Raw HTML or "various results suggest..." → useless, wastes solver turns
- Cap each direct_result content at 500 chars
- Lead with the key fact, include source attribution and date
