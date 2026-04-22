"""Prompt templates for A-Evolve."""

from __future__ import annotations

import json
from typing import Any

from ...contract.workspace import AgentWorkspace

DEFAULT_EVOLVER_SYSTEM_PROMPT = """\
You are a meta-learning agent that improves another agent by modifying its workspace files.

The workspace follows a standard directory structure:
- prompts/system.md  -- the agent's system prompt
- skills/*/SKILL.md  -- reusable skill definitions
- skills/_drafts/    -- draft skills from the solver
- memory/*.jsonl     -- episodic and semantic memory
- tools/             -- helper scripts the agent can invoke via bash
- infra/             -- infrastructure pipelines (run by framework, has network)

Each cycle you will receive:
- Task observation logs with patterns, failures, and recurring themes
- A permissions section listing which layers you CAN and CANNOT modify
- Instructions tailored to the enabled layers

Follow the permissions and instructions in each cycle message exactly.
Changes to disabled layers will be reverted automatically.

Guidelines:
- Quality over quantity. Only create artifacts that genuinely help future tasks.
- Skills use SKILL.md format with YAML frontmatter (name, description).
- Keep memory concise and actionable.
- When modifying files, use precise edits.
- Use the provided bash tool to read/write files in the workspace.
- Verify your changes with `git diff` before finishing.

Tool creation:
- Tools are helper scripts (Python or bash) the solver can run via its bash tool.
- To create a tool: write the script to tools/<name>.py, then register it in
  tools/registry.yaml under the "tools" key with name, description, and usage fields.
- Example registry.yaml entry:
    tools:
      - name: find_test_files
        description: Find test files related to a given source file
        usage: python tools/find_test_files.py <source_file>
- Only create tools for patterns you see repeated across multiple tasks.
"""


def build_evolution_prompt(
    workspace: AgentWorkspace,
    logs: list[dict[str, Any]],
    drafts: list[dict[str, str]],
    evo_number: int,
    *,
    evolve_prompts: bool = True,
    evolve_skills: bool = True,
    evolve_memory: bool = True,
    evolve_tools: bool = False,
    evolve_infra: bool = True,
    include_patches: bool = False,
    trajectory_only: bool = False,
) -> str:
    """Build the user-message prompt for one evolution cycle."""
    summaries = []
    for log in logs:
        entry: dict[str, Any] = {
            "task_id": log.get("task_id", log.get("instance_id", "")),
        }
        if not trajectory_only:
            entry["success"] = log.get("success", False)
            entry["score"] = log.get("score", 0.0)
            entry["feedback"] = log.get("feedback_detail", log.get("detail", ""))
        if include_patches and (trajectory_only or not log.get("success", False)):
            patch = log.get("agent_output", log.get("output", ""))
            if patch:
                entry["patch"] = patch
        conversation = log.get("conversation", [])
        if conversation:
            entry["trajectory"] = conversation
        summaries.append(entry)

    skills = workspace.list_skills()
    skill_names = [s.name for s in skills]

    tool_registry = workspace.read_tool_registry()
    tool_names = [t.get("name", "") for t in tool_registry]

    draft_section = "No draft skills this batch."
    if drafts:
        parts = []
        for d in drafts:
            parts.append(f"#### Draft: {d['name']}\n```markdown\n{d['content']}\n```")
        draft_section = "\n\n".join(parts)

    permission_lines = []
    if evolve_prompts:
        permission_lines.append("- You CAN modify prompts/system.md")
    else:
        permission_lines.append("- You CANNOT modify prompts/ (changes will be reverted)")
    if evolve_skills:
        permission_lines.append("- You CAN create/modify/delete skills in skills/")
    else:
        permission_lines.append("- You CANNOT modify skills/ (changes will be reverted)")
    if evolve_memory:
        permission_lines.append("- You CAN add/prune entries in memory/*.jsonl")
    else:
        permission_lines.append("- You CANNOT modify memory/ (changes will be reverted)")
    if evolve_tools:
        permission_lines.append("- You CAN create/modify tools in tools/")
    else:
        permission_lines.append("- You CANNOT modify tools/ (changes will be reverted)")
    if evolve_infra:
        permission_lines.append("- You CAN create/modify files in infra/")
    else:
        permission_lines.append("- You CANNOT modify infra/ (changes will be reverted)")

    # Only include sections for enabled layers
    sections = []
    if logs:
        sections.append(f"### Task Summaries (this batch)\n```json\n{json.dumps(summaries, indent=2)}\n```")
    if evolve_skills:
        sections.append(f"### Draft Skills\n{draft_section}")
        sections.append(f"### Current Skills\n{chr(10).join(f'- {s}' for s in skill_names) if skill_names else 'No skills yet.'}")
    if evolve_tools:
        sections.append(f"### Current Tools\n{chr(10).join(f'- {t}' for t in tool_names) if tool_names else 'No tools yet.'}")

    # Instructions matching enabled layers
    instructions = ["1. Review the task summaries -- identify patterns, common failures, recurring themes"]
    step = 2
    if evolve_skills:
        instructions.append(f"{step}. Review draft skills -- decide: refine into a real skill, merge with existing, or discard")
        step += 1
        instructions.append(f"{step}. Review current skills -- any need updating based on new evidence?")
        step += 1
    if evolve_memory:
        instructions.append(f"{step}. Review memory -- prune redundant entries, add high-level insights")
        step += 1
    if evolve_prompts:
        instructions.append(f"{step}. Improve the system prompt if needed")
        step += 1
    if evolve_tools:
        instructions.append(f"{step}. Create/update tools for recurring patterns (write script + update tools/registry.yaml)")
        step += 1
    if evolve_infra:
        instructions.append(f"{step}. Create/update infrastructure pipelines in infra/ if failures are infrastructure-level")
        step += 1
    instructions.append(f"{step}. Use the workspace_bash tool to read/write files in the workspace")
    step += 1
    instructions.append(f"{step}. Verify your changes with `git diff` before finishing")

    return f"""\
## Evolution Cycle #{evo_number}

### Permissions
{chr(10).join(permission_lines)}

{chr(10).join(sections)}

### Instructions
{chr(10).join(instructions)}

When done, summarize what you changed and why.
"""


# ── Navigation prompts ──────────────────────────────────────────────────
# The canonical home is ``agent_evolve.algorithms.navigation.prompts``.
# Lazy re-export (via ``__getattr__``) keeps legacy imports working:
#
#     from agent_evolve.algorithms.aevolve.prompts import NAVIGATE_SYSTEM_PROMPT
#
# without creating a circular dependency between ``aevolve.engine`` and
# ``navigation.engine``.


def __getattr__(name: str):
    if name in (
        "ANALYZE_PLAN_SYSTEM_PROMPT",
        "NAVIGATE_SYSTEM_PROMPT",
        "build_analyze_plan_prompt",
        "build_navigate_prompt",
    ):
        from ..navigation import prompts as _nav_prompts  # local import breaks cycle
        return getattr(_nav_prompts, name)
    raise AttributeError(name)
