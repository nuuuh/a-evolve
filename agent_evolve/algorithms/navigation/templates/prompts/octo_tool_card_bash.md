**workspace_bash** — run a bash command inside a Docker sandbox mounted at the workspace root.

When to use:
- Run Python snippets for numerical reasoning (`python3 -c "..."`)
- Read supporting files the task references (`cat`, `head`, `ls`)
- Invoke any scripts under `tools/` or `infra/`
- Check intermediate state (`ls`, `pwd`, `echo`)

Avoid:
- Do not try to install new packages — the sandbox image is fixed.
- Do not call `git commit` — the framework handles that.
- Long-running loops: per-call timeout is enforced.

One bash call per tool-use message. Don't chain many unrelated commands in a single call.
