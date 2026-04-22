"""Prompt templates for the Navigation engine.

These are the F_Navigate (task routing) and ANALYZE_PLAN (holistic
batch analysis) prompts used by NavigationEngine.  Core evolution
prompts remain in ``..aevolve.prompts`` since NavigationEngine reuses
``build_evolution_prompt`` for Step 2/3 of its pipeline.
"""

from __future__ import annotations

import json
from typing import Any


NAVIGATE_SYSTEM_PROMPT = """\
You are a task router. You will see the full workspace content (system prompt,
skills, tools) for each branch of a strategy git tree, plus a task that needs
to be solved. Examine each branch's actual capabilities and select the one
best equipped to handle this task.

Compare the branches' system prompts — they reveal each branch's approach,
techniques, and domain expertise. Compare their skills and tools — they reveal
what reusable capabilities are available.

The "main" branch is the general-purpose default. Specialized branches handle
specific problem regimes with tailored strategies. Choose based on which
branch's actual workspace content best matches what the task requires.

Output JSON only:
{"branch": "main", "confidence": 0.8, "reason": "general task, no specialist branch fits"}
"""


def build_navigate_prompt(
    task_description: str,
    branches: list[dict[str, Any]],
) -> str:
    """Build the prompt for F_Navigate with full branch workspace content."""
    branch_sections = []
    for b in branches:
        lines = [f"### {b['name']}"]
        lines.append(f"**Description:** {b.get('description', 'no description')}")

        prompt = b.get("system_prompt", "")
        if prompt:
            lines.append(f"\n**System Prompt:**\n```\n{prompt}\n```")

        skills = b.get("skills", [])
        if skills:
            lines.append(f"\n**Skills:** {', '.join(skills)}")

        tools = b.get("tools_registry", "")
        if tools:
            lines.append(f"\n**Tools Registry:**\n```yaml\n{tools}\n```")

        branch_sections.append("\n".join(lines))

    return f"""\
## Task to Route

{task_description}

## Git Tree Leaves (Branch Workspaces)

{chr(10).join(branch_sections)}

---
Select the branch best equipped to handle this task. Output JSON:
{{"branch": "<branch_name>", "confidence": <0.0-1.0>, "reason": "<why>"}}
"""


ANALYZE_PLAN_SYSTEM_PROMPT = """\
You are a meta-learning strategist for an evolving AI agent system.

The agent solves tasks that arrive in batches. Strategy-relevant properties of
tasks may shift over time — not topic labels, but the techniques required,
environment constraints, information availability, and decision structure.

The agent's workspace is version-controlled as a git tree:
- **main** branch: general-purpose strategy (domain-generalizable improvements)
- **feature branches**: specialized strategies for specific property regimes

Your job: analyze ALL experience from the latest batch, then produce a holistic
evolution plan for the entire git tree.

## Analysis Framework

For each pattern you identify, classify it:

1. STATIONARY — a domain-generalizable capability gap. Fixing this helps ALL tasks
   regardless of when they appear. The improvement transfers universally.

   Ask: "Would this fix still help if the task distribution shifts completely?"
   Examples:
   - Output format parser breaks on edge cases → fix helps every future task
   - Missing verification tool → all tasks benefit from better verification
   - Inefficient search strategy → better search helps broadly

2. NON_STATIONARY — evidence of distribution shift. The current workspace was
   optimized for a different strategic regime. These tasks require fundamentally
   different techniques, tooling, or decision strategies that would hurt other tasks
   if applied globally.

   Ask: "Would applying this fix to ALL tasks make some worse?"
   Examples:
   - Tasks now require binary reverse-engineering but workspace only has text tools
   - Information sources shifted from searchable web to closed platforms
   - Decision environment changed from high-certainty to high-uncertainty regime

## Output

Produce a JSON evolution plan:
{
  "summary": "High-level analysis of what happened this batch",
  "main_evolution": {
    "description": "What stationary improvements to make on main",
    "insights": ["insight1", "insight2"],
    "task_ids": ["ids of tasks that informed this analysis"]
  },
  "branches": [
    {
      "name": "branch/descriptive-regime-name",
      "action": "create or update",
      "description": "What property regime this branch handles",
      "evolution_guidance": "Specific changes to make on this branch",
      "task_ids": ["ids of tasks that informed this"]
    }
  ]
}

Guidelines:
- Name branches after the strategic shift (e.g., "branch/binary-analysis",
  "branch/closed-platform"), not the topic.
- Only create branches when there's genuine evidence of distribution shift.
- Include task_ids to link analysis back to specific evidence.
- If all issues are stationary, branches array should be empty.
- If everything succeeded and no improvements needed, main_evolution description
  can be empty.
- Output ONLY the JSON plan, no other text.
"""


def build_analyze_plan_prompt(
    batch_results: list[dict],
    evolution_history: list[dict],
    branches: list[str],
    *,
    trajectory_only: bool = False,
) -> str:
    """Build the prompt for holistic experience analysis and plan generation."""
    summaries = []
    for r in batch_results[:30]:  # cap to avoid prompt bloat
        entry: dict[str, Any] = {
            "task_id": r.get("instance_id", r.get("task_id", "")),
            "turns": r.get("turns", 0),
            "error": r.get("error", ""),
        }
        if not trajectory_only:
            entry["success"] = r.get("success", False)
            entry["detail"] = r.get("detail", "")[:300]
        summaries.append(entry)

    if not batch_results:
        return "No task results to analyze."

    if trajectory_only:
        header = f"## Batch Results ({len(batch_results)} tasks)"
    else:
        n_success = sum(1 for r in batch_results if r.get("success", False))
        n_fail = len(batch_results) - n_success
        header = f"## Batch Results ({len(batch_results)} tasks: {n_success} passed, {n_fail} failed)"

    return f"""\
{header}

```json
{json.dumps(summaries, indent=2)}
```

## Current Branches
{chr(10).join(f'- {b}' for b in branches) if branches else '(no branches yet, only main)'}

## Evolution History (last 5 cycles)
{json.dumps(evolution_history[-5:], indent=2) if evolution_history else '(first cycle)'}

## Instructions

1. Analyze ALL task results — identify patterns in the trajectories
2. Classify patterns as stationary (domain-generalizable) or non-stationary (distribution shift)
3. Write a holistic evolution plan for the git tree

Output the JSON evolution plan.
"""
