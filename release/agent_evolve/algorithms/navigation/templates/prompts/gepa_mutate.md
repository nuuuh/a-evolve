MUTATE — cycle {evo_number}.

You MUST produce a NEW revised version of `prompts/system.md` that addresses the critique below. Do NOT return without writing the file — an unchanged file counts as a failure of this cycle.

## Critique (the issues you must fix)
{critique}

## Current prompts/system.md (this is what you are replacing)
```
{current_prompt}
```

---

Your task:
1. Open a single workspace_bash call.
2. Inside that call, use `cat > prompts/system.md <<'GEPA_NEW_PROMPT'` ... `GEPA_NEW_PROMPT` heredoc to write a revised full-text version of `prompts/system.md` that addresses each numbered point in the critique.
3. Verify with `cat prompts/system.md | wc -c` and `git diff --name-only`.
4. Stop (do NOT commit).

Remember: only `prompts/system.md` may change. A no-op counts as failure.
