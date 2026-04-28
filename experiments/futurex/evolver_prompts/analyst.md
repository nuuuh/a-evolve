Tasks are temporal prediction questions requiring factual information
available BEFORE a cutoff date. The solver calls web_search(query)
which internally runs infra/search_pipeline.py to fetch structured
data from APIs, then falls back to Wikipedia and web search.

Identify failure regimes by what DATA SOURCE the pipeline is missing:
- Tasks where the pipeline returns no direct_results → needs a new
  handler function in search_pipeline.py for that data type
- Tasks where direct_results exist but are wrong/incomplete → the
  handler needs better parsing or a fallback API chain
- Tasks where classify() routes to the wrong handler → classification
  patterns need updating
- Tasks where the solver wastes turns despite good results → this is
  a prompt/strategy issue, not a pipeline gap

Do NOT name regimes after solver behavior (e.g. "excessive_searching").
Name them after the missing data capability (e.g. "sports_scores",
"crypto_prices", "chinese_content").
