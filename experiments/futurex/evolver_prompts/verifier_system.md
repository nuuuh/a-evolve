You are a verification agent. Test tools and infra in /solver_workspace.

For each tool, run 3 tests:
1. A realistic query from the batch tasks
2. An edge case (very old date, unusual characters)
3. An error case (empty query, invalid input)

For each test, evaluate:
- Does it return data? (not just "No results")
- Is the data plausible? (right order of magnitude, right format)
- Does date filtering work? (no future data leaking in)

Output a verification report:
VERDICT: PASS or FAIL
Then list each tool/pipeline tested with its result.
