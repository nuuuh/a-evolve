Tasks are temporal prediction questions requiring factual information
available BEFORE a cutoff date. The solver calls web_search(query)
which returns results from the evolved search pipeline + Wikipedia +
web search fallbacks.

Focus on DATA SOURCE COVERAGE gaps:
- Which query types got no structured API data (only Wikipedia/web)?
- Which data domains have zero coverage in the current pipeline?
- Which existing sources returned errors or empty results?
- Are there regional/language gaps (Chinese, Japanese, non-English)?

The more data sources the pipeline integrates, the more queries the
solver can answer. Your task board should drive research toward
discovering and integrating new sources.
