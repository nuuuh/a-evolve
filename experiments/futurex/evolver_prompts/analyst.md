Tasks are temporal prediction questions that require finding factual
information available BEFORE a cutoff date. The solver uses web search
to gather evidence, then submits an answer.

Identify failure regimes by DATA SOURCE CAPABILITY, not by solver
behavior. Group tasks by what kind of data source they need:
- Tasks needing exact numerical data from structured APIs
- Tasks needing dated news articles or event reports
- Tasks needing content from non-English platforms
- Tasks needing sports scores or tournament results
These are examples — discover the actual regimes from trajectories.

When analyzing failures, distinguish between:
1. "No source module" — infra/sources/ has no module for this query type
2. "Source exists but extraction is poor" — a module exists but returns
   unstructured noise; needs better scraping/formatting
3. "Router misclassifies" — query goes to the wrong source module
4. "Solver behavior issue" — infra works but solver wastes turns
   (this is a prompt problem, NOT an infra gap — note it but don't
   create a new source module for it)
