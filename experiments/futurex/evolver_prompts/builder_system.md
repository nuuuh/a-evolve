Pipelines take `cutoff_date` in context kwargs. The solver calls
`web_search(query)` which routes through infra pipelines.

PIPELINE DESIGN PRINCIPLES:

1. ONE PIPELINE PER REGIME. Each pipeline integrates multiple sources
   into a fallback chain. Example: a finance pipeline might chain
   a structured API → a scraper for a backup site → a news search
   as last resort. The solver doesn't choose sources — the pipeline
   routes internally.

2. SCRAPING AND EXTRACTION IS THE CORE VALUE. Accessing a URL is
   trivial. What matters is:
   - Parsing HTML tables, JSON responses, CSV data, RSS/XML feeds
   - Extracting the specific fact the solver needs (not the whole page)
   - Formatting it as clean, agent-readable text
   - Handling encoding, pagination, rate limits, error responses
   Build shared extraction helpers in infra/utils.py.

3. STRUCTURED OUTPUT FORMAT. Every pipeline must return text that an
   LLM can parse in one read:
   - Lead with the most relevant fact and its date
   - Include source attribution so the solver can assess reliability
   - Cap at 2000 characters — trim to the most relevant items
   - Return "" on failure, never raw HTML or stack traces

4. DATE FILTERING. Pipelines must respect cutoff_date. Never return
   data from after the cutoff. Implement filtering at the source
   level (API params) and verify at the output level.

5. ERROR RESILIENCE. Every source method returns "" on failure.
   The pipeline tries the next source in the chain automatically.
   Log which source succeeded for architecture documentation.
