Tasks are temporal prediction questions that require finding factual
information available BEFORE a cutoff date. The solver uses web search
to gather evidence, then submits an answer.

Discover capability regimes by reading the batch trajectories — do NOT
use a hardcoded list. Group tasks by what KIND of data they need
(e.g. if several tasks fail because they need exact numerical values
from structured databases, that's a regime). The regimes should emerge
from the actual failure patterns, not from domain labels.

When analyzing failures, distinguish between:
1. "No source available" — no pipeline covers this kind of query
2. "Source returns unstructured noise" — a pipeline exists but its
   output is too messy for the solver to extract answers from
3. "Solver uses too many turns" — the pipeline works but the solver
   doesn't use it efficiently (prompt guidance issue, not infra)
