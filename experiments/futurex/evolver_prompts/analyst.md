DOMAIN REGIMES for FutureX temporal prediction:

- finance: Stock closing prices, index values, commodity prices,
  currency exchange rates, earnings announcements. Tasks ask for
  EXACT numerical values on specific dates.

- general_news: Current events, awards (Oscars, Grammys), weather
  records, product launches. Tasks need factual answers from dated
  news articles. Google News RSS is the primary source.

- sports: Match results, tournament outcomes, rankings, player stats.
  Tasks need specific scores, winners, or standings on a given date.

- chinese_content: Douban ratings, Maoyan box office, Bilibili stats,
  Sina/Baidu search results. Tasks need data from Chinese platforms
  that are not indexed by English search engines.

- politics: Election results, polling data, legislative votes,
  approval ratings. Tasks need specific outcomes or numbers.

- technology: Product release dates, model benchmarks, company
  announcements, open-source project metrics. Tasks need facts about
  tech events before the cutoff date.

KEY INSIGHT: Tasks require web search with date cutoff — the solver
must find information available BEFORE the task's creation date.
The biggest failure mode is NOT lack of search ability but lack of
STRUCTURED data extraction. The solver wastes turns reformulating
queries when it could get exact answers from structured APIs.

When analyzing failures, distinguish between:
1. "No source available" — need new API/pipeline for this regime
2. "Source exists but returns unstructured noise" — need better
   scraping/extraction in the pipeline
3. "Source works but solver doesn't use it efficiently" — need
   better prompt guidance, not more tools
