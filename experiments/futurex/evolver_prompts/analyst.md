Tasks are temporal prediction questions. The solver calls web_search(query)
to gather evidence, then submits an answer.

Analyze failures by looking at what web_search RETURNED vs what the
solver NEEDED:

- "Search returned Wikipedia markup, solver needed exact price"
  → the infra pipeline needs a better data source for this query type
- "Search returned good data but solver ignored it and kept searching"
  → prompt/strategy issue, not an infra gap
- "Search returned nothing relevant"
  → the pipeline doesn't classify or handle this query type yet
- "Search returned data from after the cutoff date"
  → date filtering is broken in the pipeline

Use bash to browse /trajectories/ and /evolver_workspace/evolution/observations/
to see exactly what the solver received from web_search and how it responded.

Name regimes by what DATA CAPABILITY is missing, not by solver behavior.
