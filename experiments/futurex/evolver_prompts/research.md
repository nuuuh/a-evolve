The goal is to find data sources that can be implemented as FUNCTIONS
within a single Python file using only stdlib (urllib.request, json,
re, xml.etree). The function receives a query + cutoff_date and must
return structured, agent-readable text.

For each source you test, evaluate:
1. ACCESS: Can you call it with urllib.request? No auth needed?
2. DATE FILTERING: Can it return data for a specific past date?
3. RESPONSE FORMAT: JSON or XML preferred (easy to parse with stdlib).
   HTML requires regex extraction (fragile but acceptable).
4. OUTPUT QUALITY: After parsing, does it give a clear answer?
   "Close: $237.42 on 2026-01-07" is good. Raw dumps are useless.
5. RELIABILITY: Works 3/3 times? Latency under 8 seconds?
6. STDLIB ONLY: Can the full request → parse → format chain be done
   with urllib + json + re? No requests, beautifulsoup, or htmldate.

SOURCE CATEGORIES:
- Structured APIs: Yahoo Finance, FRED, TheSportsDB, Open-Meteo,
  CoinGecko, Wikidata SPARQL (return JSON with exact values)
- RSS feeds: Google News RSS, podcast feeds (return XML with dates)
- Wikipedia API: search + extracts + historical revisions
- AI search APIs (KEY-GATED — document credential_needed):
  Serper (Google SERP as JSON), Jina Reader (clean markdown from URLs),
  Tavily (AI search), Exa (semantic search with date filtering)
- For key-gated sources: test if the endpoint responds, log
  credential_needed=true so HITL can supply keys later

Document for the builder: which function name it should go under
(e.g. _sports, _crypto), the exact urllib call, and parsing steps.
