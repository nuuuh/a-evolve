Pipelines take `cutoff_date` in context kwargs. The solver calls
`web_search(query)` which routes through infra.

TARGET INFRA STRUCTURE:
```
infra/
  __init__.py
  router.py           # classify query → dispatch to right source
  utils.py            # shared: HTML→text, JSON parsing, date filter, output format
  sources/
    <source>.py       # one module per data source CAPABILITY
```

Each source module in infra/sources/ covers a DATA CAPABILITY, not a
failure mode. Examples: a finance source handles stock prices, index
values, exchange rates. A news source handles dated headlines, event
reports. Do NOT name modules after solver problems (e.g. no
"answer_format_mismatch_pipeline.py" or "turn_waste_pipeline.py").

EACH SOURCE MODULE should:
- Have a `search(query, cutoff_date) -> str` method
- Contain a fallback chain: primary API → secondary → web search
- Include scraping/extraction logic that turns raw responses into
  clean, agent-readable text (this is where the value is)
- Handle errors gracefully — return "" on failure, let router try next

THE ROUTER (infra/router.py) should:
- Classify incoming queries by capability type
- Try sources in order of specificity (structured API → general web)
- Return the first non-empty result

SHARED UTILS (infra/utils.py) should:
- HTML → text extraction
- JSON/CSV/XML parsing helpers
- Date filtering and validation
- Output formatting (cap at 2000 chars, structured format)

EVOLUTION IS INCREMENTAL:
- Cycle 1 might create 2-3 source modules + router
- Cycle 2 adds a new source module OR improves an existing one
  by adding a new API to its fallback chain
- Don't rebuild what already works — extend it
