# FutureX Benchmark Hints for Structured Evolution

## Analyst Hints
Regimes may include: finance (stock prices, indices, economic data),
sports (rankings, scores, tournament results), chinese_content
(Douban, Maoyan, Sina, Baidu results), politics (elections, polls),
technology (product releases, company news), general_news (current
events, weather, awards).

Tasks require web search with date cutoff — the solver must find
information available BEFORE the task's creation date.

## Research Hints
Test APIs with real HTTP requests in the sandbox. Prioritize:
- Date-filtered sources (historical data, not just "latest")
- Sources that return structured/parseable data (CSV, JSON, API)
- Multiple sources per regime for fallback chains

Common source categories to explore:
- Financial data APIs (stock prices, indices, commodities)
- Chinese search engines and data platforms
- Sports statistics APIs and databases
- News aggregators with date filtering
- Prediction markets and forecasting platforms

Check: does the source return data for a specific past date?
Check: is the data precise enough (exact prices, scores)?
Check: does it work reliably (3/3 test queries succeed)?

## Builder Hints
Pipelines take `cutoff_date` in context kwargs. The solver calls
`web_search(query)` which routes through infra pipelines.

The solver has an 80-turn budget and manages it — never limit the
solver's search count in prompts/system.md.

Google News RSS at `https://news.google.com/rss/search?q=...`
returns timestamped headlines without needing htmldate. Build a
news search pipeline using this source as a first priority.
