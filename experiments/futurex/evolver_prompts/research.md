Find as many useful data sources as possible for the assigned regime.
The value comes from BREADTH — discovering sources the previous cycles
missed. Don't stop at the first one that works.

For each regime, explore broadly:
- Public APIs (REST, RSS, GraphQL) with structured responses
- Websites with scrapeable structured data (tables, lists, feeds)
- Specialized databases and archives with historical data
- Search engines with date-range filtering
- Regional/language-specific platforms
- Key-gated APIs (document credential_needed=true for HITL)

For each source you test, evaluate:
1. What query types does it cover? What does it NOT cover?
2. Can it return data for a specific past date?
3. Is the response parseable with stdlib? (JSON/XML/CSV >> HTML)
4. Does it work reliably? (3/3 calls succeed, <8s each)
5. How does it COMPLEMENT other sources in this regime?

The goal: give the builder a rich menu of verified sources to
integrate. Multiple sources per regime means fallback chains and
broader coverage.

Write findings to /evolver_workspace/tests/research_{regime}.jsonl.
