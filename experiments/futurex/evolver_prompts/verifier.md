Test the search pipeline at /solver_workspace/infra/search_pipeline.py:

Run it via subprocess:
  echo '{{"query": "<sample_query>", "cutoff_date": "{cutoff_date}"}}' | python3 /solver_workspace/infra/search_pipeline.py

For each data category the pipeline handles, verify:

1. DIRECT RESULTS: Does it return specific, extractable answers?
   "AAPL close: $237.42 on 2026-01-07" → PASS
   Empty list or vague text → FAIL

2. DATE COMPLIANCE: Do all direct_results have dates before cutoff?
   Any post-cutoff data → FAIL

3. CLASSIFICATION: Does classify() route different query types
   correctly? Test a finance query, a news query, a general query.

4. FALLBACK: If the primary API fails (bad ticker, timeout), does
   the handler return [] gracefully without crashing?

5. QUERIES: Does the pipeline generate useful alternative search
   terms in the "queries" field?

6. FORMAT: Output is valid JSON with optional direct_results and
   queries fields. Script exits 0. Completes under 15 seconds.

Test with diverse queries: a stock price, a news event, a sports
result, and a query in the "general" category.
