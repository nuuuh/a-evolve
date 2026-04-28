The goal is to DISCOVER and EVALUATE diverse data sources that can
answer temporal prediction questions. Do not limit yourself to obvious
sources — the value comes from finding sources the previous evolution
cycles missed.

For each regime assigned to you, explore broadly:
- Public APIs (REST, RSS, GraphQL) with structured responses
- Websites that can be scraped for structured data (tables, lists)
- Specialized databases and archives with historical data
- Search engines with date-range filtering capabilities
- Regional/language-specific platforms (not just English sources)

For each source you test, evaluate the FULL pipeline viability:
1. ACCESS: Can you reach it from the sandbox? Any auth needed?
2. DATE FILTERING: Can it return data for a specific past date,
   or only "latest"? Historical data is far more valuable.
3. RAW RESPONSE FORMAT: Is it JSON, CSV, HTML, XML/RSS, plain text?
4. SCRAPING COMPLEXITY: How much parsing is needed to extract the
   answer? A JSON API returning exact values is better than an HTML
   page requiring BeautifulSoup + regex.
5. OUTPUT QUALITY: After extraction, would an LLM get the answer in
   one read? "Exact value: 42.5 on 2026-01-15" is good. A wall of
   HTML or "various results suggest..." is useless.
6. RELIABILITY: Does it work 3/3 times? Latency under 10 seconds?
7. COMPLEMENTARITY: What does this source cover that others don't?
   Document gaps so the builder knows where fallbacks are needed.

Remember: the hard part is NOT finding a URL that returns data.
The hard part is building a reliable extraction path that turns raw
responses into clean, structured, agent-readable text.
