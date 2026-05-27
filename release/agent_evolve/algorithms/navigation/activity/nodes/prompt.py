"""Prompt-building actions.

Thin wrappers around existing prompt builders:
  - ``aevolve.prompts.build_evolution_prompt``
  - ``navigation.prompts.build_navigate_prompt`` (routing only)
  - ``navigation.templates.inline.build_branching_section``
  - ``navigation.templates.orchestrated.build_analyze_plan_prompt``

Template-specific prompts are owned by their respective template files;
these actions just pull them in on demand so specs can compose prompts
without knowing where they physically live.
"""

from __future__ import annotations

from typing import Any

from ..action import Action
from ..pin import InputPin, OutputPin
from ..types import Type


class BuildEvolutionPrompt(Action):
    """Build the standard A-Evolve evolution prompt.

    Produces the privacy-safe trajectory index + permissions stanza that
    the evolver LLM reads.
    """

    action_kind = "op.build_evolution_prompt"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="workspace", type=Type.WORKSPACE),
            InputPin(name="batch_results", type=Type.BATCH_RESULTS),
            InputPin(name="config", type=Type.CONFIG),
            InputPin(name="drafts", type=Type.STRING_LIST, required=False),
            InputPin(name="evo_number", type=Type.INTEGER, required=False),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="text", type=Type.PROMPT_TEXT)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from ....aevolve.prompts import build_evolution_prompt

        ws = inputs["workspace"]
        cfg = inputs["config"]
        drafts = inputs.get("drafts") or ws.list_drafts()
        evo_number = inputs.get("evo_number") or 0

        text = build_evolution_prompt(
            ws,
            inputs["batch_results"],
            drafts,
            evo_number,
            evolve_prompts=cfg.evolve_prompts,
            evolve_skills=cfg.evolve_skills,
            evolve_memory=cfg.evolve_memory,
            evolve_tools=cfg.evolve_tools,
            evolve_infra=cfg.evolve_infra,
            include_patches=cfg.evolver_include_patches,
            trajectory_only=cfg.trajectory_only,
        )
        return {"text": text}


class AppendBranchingSection(Action):
    """Append the branching stanza so the evolver can create branches.

    Wraps ``navigation.templates.inline.build_branching_section`` (the
    prompt lives alongside the inline template that uses it).  ``tree``
    is read from the ``GitTree`` pin (a ``(vc, StrategyTree)`` tuple).
    """

    action_kind = "op.append_branching_section"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="prompt", type=Type.PROMPT_TEXT),
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="batch_results", type=Type.BATCH_RESULTS),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="text", type=Type.PROMPT_TEXT)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from ...templates.inline import build_branching_section

        _, tree = inputs["git"]
        section = build_branching_section(tree, inputs["batch_results"])
        return {"text": inputs["prompt"] + section}


class PrependPlanContext(Action):
    """Prepend a plan context block to the evolution prompt.

    Accepts two plan shapes for backward compatibility:

      * **New shape** (preferred) — a single assignment carried on the
        ``plan`` pin::

            {"summary": "...", "assignment": {"target": "main",
                                              "focus": "search API skill",
                                              "workload": "..."}}

      * **Legacy shape** — ``{"main_evolution": {...},
        "branches": [...]}`` as written by the old analyst.

    Passthrough semantics: if ``plan`` is falsy AND no ``target`` is
    wired, the prompt is returned unchanged.
    """

    action_kind = "op.prepend_plan_context"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="prompt", type=Type.PROMPT_TEXT),
            InputPin(name="plan", type=Type.PLAN, required=False),
            InputPin(name="target", type=Type.STRING, required=False),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="text", type=Type.PROMPT_TEXT)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        plan = inputs.get("plan")
        target = inputs.get("target") or ""
        # Passthrough when no plan context is available.
        if not plan and not target:
            return {"text": inputs["prompt"]}
        plan = plan or {}
        target = target or "main"

        lines = ["## Evolution Plan Context\n"]
        if plan.get("summary"):
            lines.append(f"**Plan summary:** {plan['summary']}\n")

        # New shape — a single assignment dict on the plan.
        assignment = plan.get("assignment")
        if isinstance(assignment, dict):
            lines.append(
                f"**Your target:** `{target}`"
                + ("  (main branch)" if target == "main"
                   else "  (specialized branch)")
            )
            focus = assignment.get("focus", "")
            if focus:
                lines.append(f"**Focus:** {focus}")
            workload = assignment.get("workload", "")
            if workload:
                lines.append(f"**Workload:**\n{workload}")
            return {"text": "\n".join(lines) + "\n\n" + inputs["prompt"]}

        # Legacy shape — main_evolution / branches.
        if target == "main":
            main_evo = plan.get("main_evolution", {})
            lines.append("**Your role:** Evolve the main (general-purpose) branch.")
            lines.append(f"**Focus:** {main_evo.get('description', '')}")
            for insight in main_evo.get("insights", []):
                lines.append(f"- {insight}")
        else:
            for bp in plan.get("branches", []):
                if bp.get("name") == target:
                    lines.append(
                        f"**Your role:** Evolve the specialized branch `{target}`."
                    )
                    lines.append(f"**Branch purpose:** {bp.get('description', '')}")
                    lines.append(f"**Guidance:** {bp.get('evolution_guidance', '')}")
                    break
        return {"text": "\n".join(lines) + "\n\n" + inputs["prompt"]}


class BuildAnalyzePlanPrompt(Action):
    """Build the analyst's batch-analysis prompt.

    Wraps ``navigation.templates.orchestrated.build_analyze_plan_prompt``
    (the prompt lives alongside the orchestrated template that uses it).
    """

    action_kind = "op.build_analyze_plan_prompt"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="batch_results", type=Type.BATCH_RESULTS),
            InputPin(name="config", type=Type.CONFIG),
            InputPin(name="git", type=Type.GIT_TREE),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="text", type=Type.PROMPT_TEXT)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from ...templates.orchestrated import build_analyze_plan_prompt

        cfg = inputs["config"]
        _, tree = inputs["git"]
        text = build_analyze_plan_prompt(
            inputs["batch_results"],
            [],
            tree.branch_names() if tree else [],
            trajectory_only=cfg.trajectory_only,
        )
        return {"text": text}


BUILTINS = [
    BuildEvolutionPrompt,
    AppendBranchingSection,
    PrependPlanContext,
    BuildAnalyzePlanPrompt,
]
