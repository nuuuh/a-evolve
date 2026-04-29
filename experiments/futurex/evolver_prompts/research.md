Find data sources that return EXACT ANSWERS, not web pages.

For each regime the analyst identified, discover sources that can
turn a natural language query into a specific factual answer using
only Python stdlib (urllib.request, json, re, xml.etree).

For each source you test, evaluate:
1. Does it return the EXACT VALUE the solver needs? (e.g. a price
   number, a score, a date — not a web page about the topic)
2. Can it filter by date? (historical data >> "latest" only)
3. Is the response parseable with stdlib? (JSON/XML/CSV >> HTML)
4. Does it work reliably? (3/3 test calls succeed, <8s each)
5. What query types does it handle vs NOT handle?

For key-gated sources (need API key to access): test if the endpoint
responds, document credential_needed=true so HITL can supply keys.

Write findings to /evolver_workspace/tests/research_{regime}.jsonl.
