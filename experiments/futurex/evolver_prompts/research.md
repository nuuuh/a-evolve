REGIME TO INVESTIGATE: {regime}

ALREADY TESTED (from research_log):
{known_results}

INSTRUCTIONS:
1. Test MULTIPLE approaches for this regime in the sandbox.
2. For each, make a real HTTP request or test command.
3. Record EXACTLY what you called, what came back, whether it's usable.
4. Output ONE JSON record per line for each test with ALL fields:
{{"cycle": {evo_number}, "regime": "{regime}", "approach": "<name>", "endpoint": "<url or command>", "tested": true, "works": true/false, "latency_ms": <number>, "coverage": ["<subtypes handled>"], "does_not_cover": ["<subtypes it fails on>"], "complementary_to": ["<other approach>"], "sample_output": "<first lines of output>", "credential_needed": false, "credential_env": "", "error": "", "notes": "<usage tips>"}}
5. Test at least 2-3 different approaches per regime.

BENCHMARK CONTEXT:
Test APIs with real HTTP requests. Prioritize:
- Date-filtered sources (historical data, not just "latest")
- Sources that return structured/parseable data (CSV, JSON, API)
- Multiple sources per regime for fallback chains

Common source categories to explore:
- Financial data APIs (stock prices, indices, commodities)
- Chinese search engines and data platforms
- Sports statistics APIs and databases
- News aggregators with date filtering
- Prediction markets and forecasting platforms

Check: does the source return data for a specific past date?
Check: is the data precise enough (exact prices, scores)?
Check: does it work reliably (3/3 test queries succeed)?
