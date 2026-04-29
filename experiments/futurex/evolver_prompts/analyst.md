Tasks are temporal prediction questions. The solver calls web_search(query)
to gather evidence, then submits an answer.

The pipeline currently integrates these data sources (check architecture.md
and the existing infra/ code to see what's built). Analyze which query
types STILL lack good data source coverage:

- Which queries returned only Wikipedia/web search (no structured API data)?
- Which data domains have zero source coverage in the pipeline?
- Which existing sources returned errors or empty results?
- Are there regional/language-specific gaps (e.g. Chinese, Japanese content)?

Use bash to browse /trajectories/ and /evolver_workspace/evolution/observations/
to see what the solver actually received from web_search.

The goal: identify which NEW data sources need to be discovered and
integrated next. The more sources the pipeline covers, the more queries
the solver can answer accurately.
