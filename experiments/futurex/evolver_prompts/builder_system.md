Pipelines take `cutoff_date` in context kwargs. The solver calls
`web_search(query)` which routes through infra pipelines.

Google News RSS at `https://news.google.com/rss/search?q=...`
returns timestamped headlines without needing htmldate. Build a
news search pipeline using this source as a first priority.
