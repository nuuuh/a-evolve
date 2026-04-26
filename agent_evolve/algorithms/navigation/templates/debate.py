"""Debate evolution template — propose → critique → revise.

Two evolvers per cycle: a proposer writes changes, a critic reviews
the diff and identifies problems, then the proposer revises. The
critique step is a cheap LLM call (no bash/sandbox needed) that
catches common mistakes before they reach the solver.

Activated via config: ``orchestrator: debate``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from .orchestrated import (
    OrchestratedTemplate,
    build_planner_prompt,
    PLANNER_SYSTEM_PROMPT_FLAT,
    _load_routing_history,
)

logger = logging.getLogger(__name__)

CRITIC_SYSTEM = """\
You are a code reviewer for an evolving agent workspace. You receive
a git diff of changes made by a proposer. Your job: find problems
that will cause runtime failures or degrade performance.

Check for:
1. Import errors — does the code import packages available in the sandbox?
2. Network assumptions — does the code handle timeouts and connection errors?
3. Argument parsing — do tools accept the expected CLI arguments?
4. Date filtering — does every web tool enforce htmldate cutoff?
5. Prompt consistency — does the system prompt reference tools that exist?
6. Registry consistency — does registry.yaml match the actual .py files?

Output a JSON critique:
{
  "issues": [
    {"severity": "high", "file": "tools/web_search.py", "problem": "no timeout on urllib.request.urlopen", "fix": "add timeout=10"},
    {"severity": "low", "file": "prompts/system.md", "problem": "mentions 'sequentialthinking' tool which does not exist", "fix": "remove reference"}
  ],
  "verdict": "revise" or "accept",
  "summary": "one sentence"
}
Output ONLY the JSON.
"""


class Template(EvolutionTemplate):
    """Propose → critique → revise evolution template."""

    def __init__(self, engine):
        self.engine = engine
        self._inner = OrchestratedTemplate(engine)

    @property
    def name(self) -> str:
        return "debate"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        nav_enabled = bool(getattr(cfg, "navigation_enabled", False))
        trajectory: list[dict] = []
        mutated = False

        # Step 1: Planner
        routing_history = _load_routing_history(routing_log_path)
        plan = self._inner._run_planner(
            batch_results, routing_history, tree.branch_names(),
            navigation_enabled=nav_enabled,
        )
        assignments = list(plan.get("assignments", []) or [])
        if not assignments:
            assignments = [{"target": "main", "focus": "general",
                            "workload": plan.get("summary", "")}]
        logger.info("Planner emitted %d assignment(s): %s",
                     len(assignments), plan.get("summary", ""))
        trajectory.append({"step": "plan", "n_assignments": len(assignments)})

        # Step 2: Per assignment — propose → critique → revise
        for assignment in assignments:
            target = assignment.get("target", "main")
            try:
                vc.checkout_branch(target)
            except Exception:
                pass

            # Snapshot before proposal
            before_diff = ""
            try:
                before_diff = vc.diff_from_head()
            except Exception:
                pass

            # ── Propose ──
            result = self._inner._execute_plan_step(
                solver_workspace, batch_results, evo_number,
                assignment=assignment, target=target,
                tag_suffix=f"{target.replace('/', '-')}-propose",
            )
            propose_mutated = result.get("mutated", False)
            trajectory.append({
                "step": "propose", "target": target,
                "mutated": propose_mutated,
            })

            if not propose_mutated:
                continue

            # Get the diff for the critic
            try:
                diff_text = vc.diff_from_head()
            except Exception:
                diff_text = "(could not generate diff)"

            # ── Critique ──
            critique = self._run_critic(diff_text, solver_workspace)
            trajectory.append({
                "step": "critique", "target": target,
                "verdict": critique.get("verdict", "accept"),
                "n_issues": len(critique.get("issues", [])),
            })

            if critique.get("verdict") == "accept":
                logger.info("Critic accepted proposal")
                mutated = True
                continue

            # ── Revise ──
            logger.info(
                "Critic found %d issues, requesting revision",
                len(critique.get("issues", [])),
            )
            critique_text = json.dumps(critique, indent=2)
            revised_assignment = dict(assignment)
            revised_assignment["workload"] = (
                f"A reviewer found these issues with your previous changes:\n"
                f"```json\n{critique_text}\n```\n\n"
                f"Fix all issues. Then continue with the original workload:\n"
                f"{assignment.get('workload', '')}"
            )

            result = self._inner._execute_plan_step(
                solver_workspace, batch_results, evo_number,
                assignment=revised_assignment, target=target,
                tag_suffix=f"{target.replace('/', '-')}-revise",
            )
            trajectory.append({
                "step": "revise", "target": target,
                "mutated": result.get("mutated", False),
            })
            if result.get("mutated", False):
                mutated = True

        # Return to main
        try:
            vc.checkout_branch("main")
        except Exception:
            pass

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": plan,
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    def _run_critic(
        self, diff_text: str, workspace,
    ) -> dict:
        """Run the critic LLM on the proposer's diff."""
        # Read tool registry for cross-check
        tools = workspace.read_tool_registry()
        tool_names = [t.get("name", "") for t in tools]

        prompt = (
            f"## Git diff of proposed changes\n"
            f"```diff\n{diff_text[:8000]}\n```\n\n"
            f"## Current tool registry\n"
            f"{json.dumps(tool_names)}\n\n"
            f"Review the diff. Report issues."
        )

        llm = getattr(self.engine, "llm", None)
        if llm is None:
            return {"verdict": "accept", "issues": [], "summary": "no LLM"}

        try:
            from ....llm.bedrock import BedrockProvider
            if not isinstance(llm, BedrockProvider):
                return {"verdict": "accept", "issues": [], "summary": "no LLM"}

            response = llm.converse_loop(
                system_prompt=CRITIC_SYSTEM,
                user_message=prompt,
                tools=[], tool_executor={},
                max_tokens=4096, temperature=0.0,
            )
            import re
            for m in re.finditer(r"\{.*\}", response.content, re.DOTALL):
                try:
                    critique = json.loads(m.group(0))
                    if "verdict" in critique:
                        return critique
                except (json.JSONDecodeError, ValueError):
                    continue
        except Exception as e:
            logger.warning("Critic failed: %s", e)

        return {"verdict": "accept", "issues": [],
                "summary": "Critic could not produce report; accepting"}
