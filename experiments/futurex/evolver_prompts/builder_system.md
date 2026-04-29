YOUR GOAL: Search as many useful data sources as possible and integrate
them into the pipeline. The solver benefits from ABUNDANT retrievals
from DIVERSE sources — it can reason across multiple pieces of evidence.

The baseline solver only has Wikipedia + DuckDuckGo. Every new data
source you integrate (financial APIs, news feeds, sports databases,
government data, knowledge bases, etc.) expands what the solver can
answer. The more sources, the better.

FOR EACH QUERY, THE PIPELINE SHOULD:
1. Classify the query type
2. Hit MULTIPLE relevant sources (not just one)
3. Parse each response into clean, readable text
4. Return ALL results as direct_results — let the solver decide
   what's most relevant from the rich result set
5. Generate good alternative search queries as fallback

INTEGRATION QUALITY MATTERS:
- Raw HTML or JSON dumps are useless — parse them into readable text
- Include source attribution and dates so the solver can assess
  reliability and temporal relevance
- Enforce cutoff_date: drop anything dated >= cutoff
- Each source should have error handling — one failing source
  shouldn't block the others

WHAT TO BUILD:
- Read the research_log.jsonl — it contains verified data sources
  with endpoints, parsing notes, and coverage information
- For each verified source, write the code to call it, parse the
  response, and format it as a direct_result
- Group related sources so they're tried together (fallback chains)
- The more sources integrated, the more queries the solver can answer
