# FutureX Search Pipeline

## Strict Mode (default)

```
web_search(query)
│
├── Cap: max 15 calls per task
│
└── _strict_search(query)
    │
    ├── Layer 1: Wikipedia Revision API
    │   └── Fetches article content AS OF cutoff date
    │       (server-side, zero leakage)
    │
    ├── Layer 2: DuckDuckGo + htmldate
    │   ├── DDGS search → get URLs + snippets
    │   ├── Fetch each URL's HTML
    │   ├── Extract publication date with htmldate
    │   └── Drop results with date >= cutoff
    │
    └── Layer 3: FRED API (economic queries only)
        └── Historical time series before cutoff
            (PCE, CPI, GDP, unemployment, etc.)

    → Combine, dedup, return top 5 results
```

## Live Mode

```
web_search(query)
└── DuckDuckGo (unrestricted, no date filtering)
```

## Concurrency

- 3 workers (ThreadPoolExecutor)
- DDGS serialized via file lock (`/tmp/aevolve_ddgs.lock`)
- Wikipedia throttled at 0.15s between calls

## Disabled APIs (credits exhausted)

- Tavily (`end_date` + full content) — can replace Layer 2 if re-enabled
- Exa.ai (`endPublishedDate` + full content) — same
