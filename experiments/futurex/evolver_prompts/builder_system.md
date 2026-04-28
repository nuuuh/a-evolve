PIPELINE ARCHITECTURE FOR FUTUREX:

Pipelines take `cutoff_date` in context kwargs. The solver calls
`web_search(query)` which routes through infra pipelines.

BUILD THESE DOMAIN PIPELINES (priority order):

1. GENERAL NEWS PIPELINE (infra/news_pipeline.py)
   Source chain: Google News RSS → Wayback Machine → Wikipedia
   - Google News RSS: `https://news.google.com/rss/search?q=...&hl=en`
     Parse XML, extract titles + links + pubDate. Filter by cutoff.
   - Support multilingual: hl=zh-CN, hl=ja, hl=ko for non-English.
   - Output format: numbered list of dated headlines with snippets.

2. FINANCE PIPELINE (infra/finance_pipeline.py)
   Source chain: Yahoo Finance API → Stooq CSV → Google News fallback
   - Yahoo v8: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}`
     Parse JSON, extract exact OHLCV for the requested date.
   - Ticker resolution: accept natural queries ("NVIDIA stock price")
     and resolve to ticker symbols (NVDA).
   - Output format: "NVDA close on 2026-01-15: $142.50 (Open: $140.20,
     High: $143.80, Low: $139.90, Volume: 45.2M)"

3. SPORTS PIPELINE (infra/sports_pipeline.py)
   Source chain: ESPN API → Wikipedia tables → Google News
   - Parse match results, tournament brackets, league standings.
   - Output format: structured score/result, not narrative text.

4. CHINESE CONTENT PIPELINE (infra/chinese_pipeline.py)
   Source chain: Douban/Maoyan scraping → Baidu search → zh.wikipedia
   - Douban: parse rating from page HTML or mobile API.
   - Maoyan: parse box office figures.
   - Use appropriate User-Agent and Accept-Language headers.
   - Output format: exact number/rating, not "the movie was popular."

5. SEARCH ROUTER (infra/router.py)
   - Classify incoming query by regime (finance/sports/news/chinese/tech)
   - Route to the appropriate pipeline
   - Return the pipeline's structured output directly

CRITICAL PIPELINE DESIGN RULES:

SCRAPING IS THE HARD PART — not API access:
- Every pipeline must parse raw responses into AGENT-FRIENDLY text.
- The solver reads pipeline output and must extract an answer from it.
- Bad: returning raw HTML, full JSON blobs, or "No results found."
- Good: returning "Answer: X" or a clean numbered list of facts.

STRUCTURED OUTPUT FORMAT:
- Lead with the most relevant fact: "DJIA close on Jan 15: 43,221.55"
- Include metadata: date confirmed, source name, confidence indicators.
- For lists (news, search results): number each item, include date.
- Max 2000 characters per response — trim to the most relevant items.

ERROR HANDLING:
- Every source method returns "" on failure (not exceptions).
- The pipeline tries the next source in the chain automatically.
- Log which source succeeded so the architecture doc stays current.

CONTENT EXTRACTION HELPERS:
- HTML → text: use BeautifulSoup or regex to strip tags.
- JSON → facts: extract specific fields, format as readable text.
- CSV → answer: parse rows, find the matching date, format value.
- RSS/XML → list: extract title + pubDate + link, format as list.
These helpers should be shared across pipelines (put in infra/utils.py).
