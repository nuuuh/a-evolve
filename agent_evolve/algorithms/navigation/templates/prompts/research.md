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

{benchmark_context}
