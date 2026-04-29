Discover as many useful data sources as possible. The value comes
from BREADTH — finding sources the previous cycles missed.

LEARN FROM EXISTING WORK:
- Check /solver_workspace/tools/ for reference tool implementations
  from prior experiments (e.g. serper_search.py, jina_reader.py)
- Browse GitHub for open-source FutureX solutions and search tools
- Study how AI search APIs (Serper, Jina, Tavily, Exa) are used in
  practice — these are high-value targets for integration
- Chinese platform access (Douban, Maoyan, Eastmoney) often requires
  specialized headers or rendering — look for working examples

Explore broadly for each regime:
- Public APIs with structured responses (REST, RSS, GraphQL)
- Websites with scrapeable structured data (tables, lists, feeds)
- Specialized databases and archives with historical data
- Search engines with date-range filtering
- Regional/language-specific platforms (not just English but also Chinese)
- Key-gated APIs (document credential_needed=true for HITL)

For each source, evaluate:
1. What query types does it cover? What does it NOT cover?
2. Can it return data for a specific past date?
3. Is the response parseable with stdlib? (JSON/XML/CSV >> HTML)
4. Does it work reliably? (3/3 calls succeed, <8s each)
5. How does it complement other sources in this regime?

Multiple sources per regime means fallback chains and broader coverage.
