**search** — retrieve web evidence via the workspace's search pipeline.

The exact invocation depends on the benchmark. Inspect `tools/registry.yaml` and `infra/` at the start of each task:
```
ls tools/ infra/
cat tools/registry.yaml
```

Typical usage:
- `python3 infra/search_pipeline.py '<json context>'` with a JSON dict containing at least `{"query": "...", "cutoff_date": "YYYY-MM-DD"}`
- Or a simple `tools/search_*.py` script with the query as stdin or argv

When to use:
- Any factual claim about events, people, or numbers you aren't certain of
- Any task whose answer depends on information not in the task statement
- Cross-checking a computed answer against an authoritative source

Evidence quality:
- Prefer primary sources (official sites, government/regulatory releases, academic papers).
- If two sources disagree, search for a tiebreaker.
- Respect any `cutoff_date` constraint in the task — restrict results accordingly.
- Search results may be noisy; extract the relevant fact yourself rather than trusting snippets.
