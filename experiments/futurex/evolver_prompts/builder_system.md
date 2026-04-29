YOUR GOAL: Make web_search return the exact answer as result #1.

The solver calls web_search("NVDA stock price January 15 2026") and
gets back a string of numbered results. If result #1 contains the
exact price, the solver gets it right in one search. If it contains
Wikipedia markup about NVIDIA's founding, the solver wastes 10 more
searches and probably gets it wrong.

BEFORE (what bad results look like — wastes solver turns):
  1. NVIDIA Corporation
     [Wikipedia rev 2026-01-20] | type = Public | traded_as =
     NASDAQ: NVDA | founded = January 1993 | ...
  → Solver reads this, learns nothing about the price, searches again

AFTER (what good results look like — solver answers immediately):
  1. NVDA price 2026-01-15
     [Yahoo Finance 2026-01-15] NVDA close: $237.42 (High: $239.10,
     Low: $235.80, Vol: 52.3M)
  → Solver reads exact price, submits answer

YOUR CODE produces the "AFTER" results by calling structured APIs
and returning them as direct_results. The framework puts your
direct_results at the TOP of web_search output, before Wikipedia
and web search fallbacks.

QUALITY BAR:
- Exact numbers, not narratives ("$237.42" not "the stock rose")
- Dated and attributed ("[Yahoo Finance 2026-01-15]")
- Pre-cutoff enforced (drop anything dated >= cutoff_date)
- Under 500 chars per result — the key fact first
- If your code can't answer, return empty direct_results and good
  alternative queries — the framework's web search will handle it

WHAT KILLS PERFORMANCE:
- Returning raw HTML or JSON blobs
- Returning vague summaries ("various sources suggest...")
- Crashing or timing out (>20s) — blocks the entire search
- Ignoring cutoff_date — future data leaks invalidate answers
