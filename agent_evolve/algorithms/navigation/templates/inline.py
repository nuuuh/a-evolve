"""Inline evolution template -- single sandboxed LLM call with git access.

Thin wrapper over the ``activity`` runtime.  The evolution flow is
expressed as an ``Activity`` (see ``activity/specs/inline.py``); this
template binds workspace / git / config / batch to the Activity's
parameters and translates its outputs back into the engine's return
contract.

Template-specific prompt (``build_branching_section``) lives here so
that moving or replacing the template is a single-file operation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..activity.registry import default_registry
from ..activity.runtime import ActivityRuntime, RunContext
from ..activity.specs.inline import build_inline_activity
from .base import EvolutionTemplate

if TYPE_CHECKING:
    from ....contract.workspace import AgentWorkspace
    from ....engine.versioning import VersionControl
    from ....types import StrategyTree
    from ..engine import NavigationEngine

logger = logging.getLogger(__name__)


def build_branching_section(
    tree: Any,
    batch_results: list[dict],
) -> str:
    """Build the branching stanza appended to the inline evolution prompt.

    Describes existing branches + their stats and instructs the evolver
    to create/evolve branches directly via ``workspace_bash`` in the
    sandbox.  Used only in inline mode.
    """
    branch_lines = []
    if hasattr(tree, "branches") and tree.branches:
        for b in tree.branches:
            pct = (b.total_passed / b.total_tasks * 100) if b.total_tasks > 0 else 0
            branch_lines.append(
                f"- **{b.name}**: {b.description or 'no description'} "
                f"({b.total_passed}/{b.total_tasks} passed, {pct:.0f}%)"
            )
    else:
        branch_lines.append("(no branches yet — only main)")

    n_tasks = len(batch_results)
    n_success = sum(1 for r in batch_results if r.get("success", False))

    return f"""

## Branch-Aware Evolution

This workspace is version-controlled as a git tree with a main branch
and optional specialized branches. You are currently evolving **main**.
You have full git access via workspace_bash.

### Current Strategy Tree

{chr(10).join(branch_lines)}

### Batch Summary

{n_tasks} tasks this cycle ({n_success} passed, {n_tasks - n_success} failed/unknown).

### Exploring Existing Branches

Before deciding whether to create new branches or update existing ones,
explore what each branch contains:

```bash
# See what's different on a branch vs main
git diff main..branch/<name> --stat
git show branch/<name>:prompts/system.md
git show branch/<name>:skills/       # list skills on the branch

# See recent branch evolution history
git log --oneline main..branch/<name>
```

This helps you decide whether an existing branch already handles a pattern
you've identified, or whether it needs updating.

### Branching Instructions

After making your workspace changes on main, analyze the batch results for
evidence of **distribution shift** — patterns where tasks require fundamentally
different techniques that would hurt other tasks if applied globally.

If you identify such patterns, create or update branches directly using git:

1. **Commit your main changes first:**
   ```bash
   git add -A && git commit -m "main: <summary of stationary improvements>"
   ```

2. **Create a new branch** or **update an existing one:**

   To create a new branch:
   ```bash
   git checkout -b branch/<descriptive-regime-name> main
   ```

   To update an existing branch:
   ```bash
   git checkout branch/<existing-branch-name>
   ```

   Use lowercase, hyphenated names describing the strategic shift
   (e.g., `branch/binary-analysis`, `branch/high-uncertainty`).

3. **Evolve the branch workspace** — edit prompts, skills, memory, tools
   to specialize for this regime. Changes here should be tailored — do NOT
   generalize across all task types.

4. **Create or update README.md** at the workspace root describing:
   - **Purpose:** what regime/property this branch handles
   - **Strategy:** the approach and key techniques
   - **Key artifacts:** which files were added or modified and why

   Example:
   ```markdown
   # Branch: branch/high-uncertainty

   ## Purpose
   Markets with price between 0.4-0.6 where evidence is weak.

   ## Strategy
   - Calibration heuristic for uncertain predictions
   - Hedging when evidence is contradictory

   ## Key Artifacts
   - skills/calibration_heuristic/SKILL.md
   - Modified prompts/system.md with uncertainty framing
   ```

5. **Commit the branch changes:**
   ```bash
   git add -A && git commit -m "branch/<name>: <summary of specialized changes>"
   ```

6. **Return to main** when done:
   ```bash
   git checkout main
   ```

Repeat steps 2-6 for each branch you want to create or update.

Guidelines:
- Only create branches for genuine non-stationary shifts, not one-off failures.
- Name branches after the strategic shift, not the topic.
- If all issues are stationary (domain-generalizable), just evolve main — no
  branches needed.
- Always verify branch operations succeeded: `git branch --list`
- Always return to main before finishing.
"""


class InlineTemplate(EvolutionTemplate):
    """Inline evolution: single LLM call with git access."""

    def __init__(self, engine: NavigationEngine):
        self.engine = engine
        self._activity = build_inline_activity()
        self._registry = default_registry()

    @property
    def name(self) -> str:
        return "inline"

    def execute(
        self,
        vc: VersionControl,
        solver_workspace: AgentWorkspace,
        batch_results: list[dict[str, Any]],
        tree: StrategyTree,
        evo_number: int,
        routing_log_path: Path | None,
    ) -> dict[str, Any]:
        runtime = ActivityRuntime(self._registry)
        ctx = RunContext(registry=self._registry, runtime=runtime)
        ctx.extra["engine"] = self.engine

        bindings = {
            "workspace": solver_workspace,
            "git": (vc, tree),
            "batch": batch_results,
            "cfg": self.engine.config,
            "evo_number": evo_number,
        }

        outputs = runtime.run(self._activity, bindings, ctx=ctx)

        report = outputs.get("mutated") or outputs.get("diff.report") or {}
        main_mutated = bool(report.get("mutated", False))
        new_branches = outputs.get("discover.new_branches", []) or []
        llm_response = outputs.get("call.response", {}) or {}
        mutated = main_mutated or bool(new_branches)

        trajectory = [{
            "step": "evolve_inline",
            "mutated": main_mutated,
            "new_branches": sorted(new_branches),
            "total_branches": sorted(vc.list_branches()),
            "conversation": llm_response.get("conversation", []),
        }]

        if mutated:
            logger.info(
                "Inline evolution: main_mutated=%s, new_branches=%s",
                main_mutated, sorted(new_branches),
            )

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
