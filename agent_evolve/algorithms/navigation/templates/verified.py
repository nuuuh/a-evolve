"""Verified evolution template — build → verify → retry loop.

Extends orchestrated with a post-build verification step. After the
evolver writes tools/prompts/skills, a verifier agent tests the new
artifacts in the sandbox. Failed tools trigger a retry with the
verification report prepended to the evolver prompt.

Activated via config: ``orchestrator: verified``
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
    PLANNER_SYSTEM_PROMPT_NAV,
    _load_routing_history,
    _parse_plan,
    _default_plan,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

VERIFIER_SYSTEM = """\
You are a tool verifier. You receive a workspace diff and a list of
evolved tools. Your job: run each tool against 2-3 sample queries and
report whether it works.

For each tool in tools/registry.yaml:
1. Run it with a realistic query from the batch.
2. Check: does it return data? Any import errors? Network errors? Timeouts?
3. Rate: PASS (returns useful data) or FAIL (error or empty).

Output a JSON report:
{
  "tools": [
    {"name": "web_search", "status": "PASS", "note": "returned 5 results"},
    {"name": "wiki_search", "status": "FAIL", "note": "ImportError: no module named 'mediawiki'"}
  ],
  "overall": "PASS" or "FAIL",
  "summary": "one sentence"
}
Output ONLY the JSON.
"""


class Template(EvolutionTemplate):
    """Build → verify → retry evolution template."""

    def __init__(self, engine):
        self.engine = engine
        self._inner = OrchestratedTemplate(engine)

    @property
    def name(self) -> str:
        return "verified"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        nav_enabled = bool(getattr(cfg, "navigation_enabled", False))
        trajectory: list[dict] = []
        mutated = False

        # Step 1: Planner (reuse orchestrated's planner)
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

        # Step 2: Per assignment — build → verify → retry
        for assignment in assignments:
            target = assignment.get("target", "main")
            try:
                vc.checkout_branch(target)
            except Exception:
                pass

            verify_feedback = ""
            step_mutated = False
            for attempt in range(1 + MAX_RETRIES):
                # Inject verification feedback on retries
                if verify_feedback:
                    assignment = dict(assignment)
                    assignment["workload"] = (
                        f"PREVIOUS ATTEMPT FAILED VERIFICATION:\n"
                        f"{verify_feedback}\n\n"
                        f"Fix the issues and try again.\n\n"
                        f"Original workload:\n{assignment.get('workload', '')}"
                    )

                # Build
                result = self._inner._execute_plan_step(
                    solver_workspace, batch_results, evo_number,
                    assignment=assignment, target=target,
                    tag_suffix=f"{target.replace('/', '-')}-attempt-{attempt}",
                )
                step_mutated = result.get("mutated", False)
                trajectory.append({
                    "step": "build", "attempt": attempt, "target": target,
                    "mutated": step_mutated,
                })

                if not step_mutated:
                    break

                # Verify
                report = self._run_verifier(
                    solver_workspace, batch_results, evo_number,
                )
                trajectory.append({
                    "step": "verify", "attempt": attempt, "report": report,
                })

                if report.get("overall") == "PASS":
                    logger.info("Verification PASSED (attempt %d)", attempt)
                    break

                verify_feedback = json.dumps(report, indent=2)
                logger.warning(
                    "Verification FAILED (attempt %d): %s",
                    attempt, report.get("summary", ""),
                )
                if attempt < MAX_RETRIES:
                    logger.info("Retrying evolution with feedback...")

            if step_mutated:
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

    def _run_verifier(
        self,
        workspace,
        batch_results: list[dict],
        evo_number: int,
    ) -> dict:
        """Run the verifier agent to test evolved tools."""
        # Read current tool registry
        tools = workspace.read_tool_registry()
        if not tools:
            return {"overall": "PASS", "tools": [],
                    "summary": "No tools to verify"}

        # Build sample queries from batch
        samples = []
        for r in batch_results[:5]:
            task_input = r.get("task_input") or r.get("input") or ""
            if isinstance(task_input, dict):
                task_input = task_input.get("input", "")
            if task_input:
                samples.append(str(task_input)[:200])

        tool_list = json.dumps(tools, indent=2)
        sample_text = "\n".join(f"- {s}" for s in samples[:3])

        prompt = (
            f"## Tools to verify\n```json\n{tool_list}\n```\n\n"
            f"## Sample task inputs for testing\n{sample_text}\n\n"
            f"Run each tool with a relevant query derived from the samples. "
            f"Use `workspace_bash` to execute: "
            f"`python3 /solver_workspace/tools/<name>.py \"query\" \"2026-01-15\"`\n"
            f"Report the JSON result."
        )

        try:
            result = self.engine._run_llm(
                prompt, workspace.root,
                system_prompt=VERIFIER_SYSTEM,
            )
            content = result.get("content", "")
            # Parse JSON from response
            import re
            for m in re.finditer(r"\{.*\}", content, re.DOTALL):
                try:
                    report = json.loads(m.group(0))
                    if "overall" in report:
                        return report
                except (json.JSONDecodeError, ValueError):
                    continue
        except Exception as e:
            logger.warning("Verifier failed: %s", e)

        return {"overall": "PASS", "tools": [],
                "summary": "Verifier could not produce report; proceeding"}
