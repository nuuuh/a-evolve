PROPOSE — cycle {evo_number}.

Status:
- Archived candidates from prior cycles: {num_archived}
- Current batch size: {batch_size}

Steps:
1. Browse `evolution/candidates/` to understand what has been tried. Use `ls`, `cat meta.json`, and `head -20 traces/batch.jsonl` on the last 2–3 cycles.
2. Read the current workspace — `prompts/system.md`, any existing skills/tools/memory/infra — to know the state you're building on.
3. Form one coherent hypothesis about what's limiting the agent right now (from behavioral evidence in traces, not scores).
4. Apply ONE minimal change (to prompts, skills, memory, tools, infra, and/or harness.py) that tests that hypothesis.
5. Verify with `git diff --name-only` that your edits are in-scope and intentional.

Do NOT commit. Do NOT touch `evolution/`. Produce one proposal, then stop.
