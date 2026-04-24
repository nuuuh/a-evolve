"""Prompt templates shared by every evolution template.

Only **routing-time** prompts live here — the F_Navigate system prompt
and the helper that renders each branch's workspace content for the
routing LLM.  These are consumed by ``NavigationEngine.navigate`` and
are used regardless of which evolution template is active.

Template-specific prompts (batch analysis, inline branching guidance)
live alongside the template file that uses them:

  - ``templates/orchestrated.py`` owns ``ANALYZE_PLAN_SYSTEM_PROMPT`` +
    ``build_analyze_plan_prompt``.
  - ``templates/inline.py`` owns ``build_branching_section``.
"""

from __future__ import annotations

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

        readme = b.get("readme", "")
        if readme:
            lines.append(f"\n**README:**\n```\n{readme}\n```")

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
