"""Adaptive evolution template — state-driven dispatch with escalation.

No LLM planner. Instead, deterministic workspace state inspection
decides which mutation operator to dispatch:

  - no tools       → ToolBuilder (build from scratch)
  - tools + errors → Debugger (fix broken tools)
  - tools ok, flat → Strategist (rethink approach, with escalation)
  - tools ok, up   → Refiner (small improvements)

Patience counters track consecutive non-improving cycles and trigger
tiered escalation: tweak → restructure → paradigm shift.

Inspired by MLEvolve's MCGS state-based dispatch (P2) and tiered
escalation (P4).

Activated via config: ``orchestrator: adaptive``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from .orchestrated import OrchestratedTemplate

logger = logging.getLogger(__name__)

# ── Role-specific system prompts ──

TOOL_BUILDER_SYSTEM = """\
You are a TOOL BUILDER. The solver workspace has no working external-data
tools. Your job: build 2-3 web search tools under tools/*.py so the solver
can gather evidence for its predictions.

Priority order:
1. A general web search tool (DuckDuckGo HTML scraping or Google News RSS)
2. A Wikipedia revision API tool (zero-leakage by construction)
3. A domain-specific API tool (finance, sports, prediction markets)

Every tool must:
- Accept (query, cutoff_date) as CLI args
- Use htmldate for date filtering on web content
- Handle timeouts and network errors gracefully
- Print results to stdout

Register all tools in tools/registry.yaml.
Update prompts/system.md to teach the solver how to use each tool.
Commit: git add -A && git commit -m "tools: <summary>"
"""

DEBUGGER_SYSTEM = """\
You are a TOOL DEBUGGER. The solver's evolved tools have a high error rate.
Your job: fix the broken tools so they reliably return data.

Steps:
1. Read tools/registry.yaml to see what tools exist.
2. Test each tool with workspace_bash: python3 tools/<name>.py "test query" "2026-01-15"
3. For each failure: diagnose (ImportError? timeout? bad URL? bad parsing?)
4. Fix the tool code, then re-test to confirm it works.
5. If a tool is unfixable, remove it from the registry.

Commit: git add -A && git commit -m "debug: <summary>"
"""

STRATEGIST_SYSTEM_TWEAK = """\
You are a STRATEGY REFINER. The solver's tools work but the pass rate is
stagnant. Make targeted improvements to prompts and skills.

Focus on:
- Is the system prompt teaching the solver to use tools effectively?
- Are there domain-specific skills that could help (sports, finance, etc.)?
- Is the solver searching with good queries, or wasting turns?

Do NOT rebuild tools from scratch — they are working.
Commit: git add -A && git commit -m "strategy: <summary>"
"""

STRATEGIST_SYSTEM_RESTRUCTURE = """\
You are a STRATEGY RESTRUCTURER. The solver's tools work but the pass rate
has been flat for multiple cycles. Minor tweaks are not enough.

Consider more significant changes:
- Replace the system prompt entirely with a new approach
- Reorganize skills into a different structure
- Change the search workflow (e.g., search → verify → search again)
- Add new tool types that complement existing ones

Do NOT remove working tools — build on them.
Commit: git add -A && git commit -m "restructure: <summary>"
"""

STRATEGIST_SYSTEM_PARADIGM = """\
You are a PARADIGM SHIFTER. The solver's evolution has been stagnant for
3+ cycles despite working tools. Something fundamental needs to change.

Consider radical approaches:
- Entirely different data sources (prediction markets instead of news?)
- Different reasoning frameworks (Bayesian, base-rate, ensemble?)
- Different tool architecture (one mega-tool vs many specialized tools?)
- Completely rewrite the system prompt from scratch

This is the last resort before giving up on this strategy.
Commit: git add -A && git commit -m "paradigm: <summary>"
"""

REFINER_SYSTEM = """\
You are a WORKSPACE REFINER. The solver is improving — make small,
targeted improvements without disrupting what works.

Focus on:
- Memory curation: add useful lessons, prune outdated entries
- Skill refinement: sharpen existing skills based on recent results
- Tool polish: improve error messages, add retry logic, optimize
- Prompt tuning: small wording changes that improve clarity

Do NOT make large structural changes. If it ain't broke, don't fix it.
Commit: git add -A && git commit -m "refine: <summary>"
"""

ESCALATION_TIERS = [
    ("tweak", STRATEGIST_SYSTEM_TWEAK),
    ("restructure", STRATEGIST_SYSTEM_RESTRUCTURE),
    ("paradigm", STRATEGIST_SYSTEM_PARADIGM),
]


class Template(EvolutionTemplate):
    """State-driven dispatch with patience-based escalation."""

    def __init__(self, engine):
        self.engine = engine
        self._inner = OrchestratedTemplate(engine)
        self._patience = 0          # consecutive non-improving cycles
        self._prev_pass_count = -1  # previous batch pass count

    @property
    def name(self) -> str:
        return "adaptive"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []

        # ── State inspection (deterministic, no LLM) ──
        tools = solver_workspace.read_tool_registry()
        n_tools = len(tools)

        # Count revealed pass/fail from batch.
        revealed = [r for r in batch_results if "success" in r]
        pass_count = sum(1 for r in revealed if r.get("success"))

        # Track improvement.
        if self._prev_pass_count >= 0:
            improved = pass_count > self._prev_pass_count
            if improved:
                self._patience = 0
            else:
                self._patience += 1
        self._prev_pass_count = pass_count

        # Deterministic tool health check.
        tool_health = self._test_tool_health(solver_workspace, batch_results)

        # Decide role(s) to dispatch.
        dispatches = self._decide_dispatches(
            n_tools, tool_health, pass_count,
        )

        trajectory.append({
            "step": "state_inspection",
            "n_tools": n_tools,
            "tool_health": tool_health,
            "tools_tested": tool_health["n_tested"],
            "tool_error_rate": tool_health["error_rate"],
            "failed_tools": tool_health["failed_tools"],
            "pass_count": pass_count,
            "patience": self._patience,
            "dispatches": [d[0] for d in dispatches],
        })
        logger.info(
            "Adaptive state: tools=%d (health: %d/%d pass, error_rate=%.2f), "
            "pass=%d/%d, patience=%d → dispatching: %s",
            n_tools, tool_health["n_pass"], tool_health["n_tested"],
            tool_health["error_rate"],
            pass_count, len(batch_results), self._patience,
            [d[0] for d in dispatches],
        )

        # ── Execute each dispatch ──
        mutated = False
        for role_name, system_prompt in dispatches:
            try:
                vc.checkout_branch("main")
            except Exception:
                pass

            from ....algorithms.aevolve.prompts import build_evolution_prompt
            cfg = self.engine.config
            base_prompt = build_evolution_prompt(
                solver_workspace, batch_results, drafts=[],
                evo_number=evo_number,
                evolve_prompts=cfg.evolve_prompts,
                evolve_skills=cfg.evolve_skills,
                evolve_memory=cfg.evolve_memory,
                evolve_tools=cfg.evolve_tools,
                evolve_infra=cfg.evolve_infra,
            )

            full_prompt = base_prompt
            try:
                result = self.engine._run_llm(
                    full_prompt, solver_workspace.root,
                    system_prompt=system_prompt,
                )
                vc.commit(
                    message=f"evo-{evo_number}-{role_name}: adaptive evolution",
                    tag=f"evo-{evo_number}-{role_name}",
                )
                # Detect mutation from actual diff, not just our commit.
                step_mutated = bool(vc.get_diff_stat("HEAD~1", "HEAD").strip())
            except Exception as e:
                logger.warning("Adaptive %s failed: %s", role_name, e)
                step_mutated = False

            trajectory.append({
                "step": role_name,
                "mutated": step_mutated,
            })
            if step_mutated:
                mutated = True

            logger.info("Adaptive %s: mutated=%s", role_name, step_mutated)

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {"summary": f"adaptive dispatch: {[d[0] for d in dispatches]}"},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    def _test_tool_health(
        self,
        workspace,
        batch_results: list[dict],
    ) -> dict:
        """Deterministic tool health check: execute each registered tool
        with sample queries and measure runtime failures.

        Resolves invocation in priority order:
          1. Registry ``command`` field (with {query}/{cutoff_date} substitution)
          2. Registry ``path`` field
          3. Fallback: ``tools/{name}.py`` with positional args

        Tests 2-3 sample queries derived from the batch.

        Returns: {n_tested, n_pass, n_fail, error_rate, failed_tools}
        """
        import shlex
        import subprocess
        tools = workspace.read_tool_registry()
        if not tools:
            return {"n_tested": 0, "n_pass": 0, "n_fail": 0,
                    "error_rate": 0.0, "failed_tools": []}

        sample_queries = []
        for r in batch_results[:5]:
            inp = r.get("task_input") or r.get("input") or ""
            if isinstance(inp, dict):
                inp = inp.get("input", "")
            if inp:
                sample_queries.append(str(inp)[:100])
            if len(sample_queries) >= 3:
                break
        if not sample_queries:
            sample_queries = ["test query 2026"]

        cutoff = "2026-01-15"
        n_pass = 0
        n_fail = 0
        failed_tools: list[str] = []
        failure_categories: dict[str, int] = {
            "missing_script": 0,
            "parse_error": 0,
            "nonzero_exit": 0,
            "timeout": 0,
            "empty_output": 0,
            "other": 0,
        }

        for t in tools:
            name = t.get("name", "")
            tool_passed = False

            for query in sample_queries:
                cmd = self._resolve_tool_command(
                    t, workspace, query, cutoff,
                )
                if cmd is None:
                    n_fail += 1
                    failed_tools.append(f"{name}: no executable script found")
                    failure_categories["missing_script"] += 1
                    break

                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True, text=True, timeout=15,
                        cwd=str(workspace.root),
                    )
                    if proc.returncode != 0:
                        stderr = (proc.stderr or "")[:100]
                        failed_tools.append(
                            f"{name}: exit {proc.returncode} ({stderr})")
                        n_fail += 1
                        failure_categories["nonzero_exit"] += 1
                        break
                    elif not proc.stdout.strip():
                        failed_tools.append(f"{name}: empty output")
                        n_fail += 1
                        failure_categories["empty_output"] += 1
                        break
                    else:
                        tool_passed = True
                except subprocess.TimeoutExpired:
                    failed_tools.append(f"{name}: timeout (>15s)")
                    n_fail += 1
                    failure_categories["timeout"] += 1
                    break
                except Exception as e:
                    failed_tools.append(f"{name}: {e}")
                    n_fail += 1
                    failure_categories["other"] += 1
                    break

            if tool_passed:
                n_pass += 1

        n_tested = n_pass + n_fail
        error_rate = n_fail / max(n_tested, 1)
        return {
            "n_tested": n_tested,
            "n_pass": n_pass,
            "n_fail": n_fail,
            "error_rate": error_rate,
            "failed_tools": failed_tools,
            "failure_categories": failure_categories,
        }

    @staticmethod
    def _resolve_tool_command(
        entry: dict, workspace, query: str, cutoff: str,
    ) -> list[str] | None:
        """Build the invocation command for a registry tool entry.

        Always returns a list (argv) so the caller never needs shell=True.
        """
        import shlex

        # Priority 1: registry `command` with template substitution.
        command_tpl = entry.get("command", "")
        if command_tpl:
            rendered = command_tpl.replace("{query}", query).replace(
                "{cutoff_date}", cutoff
            ).replace("{url}", query)
            try:
                return shlex.split(rendered)
            except ValueError:
                return None

        # Priority 2: registry `path` field.
        path = entry.get("path", "")
        if path:
            script = workspace.root / path
            if script.exists():
                return ["python3", str(script), query, cutoff]

        # Priority 3: fallback to tools/{name}.py with positional args.
        name = entry.get("name", "")
        script = workspace.tools_dir / f"{name}.py"
        if script.exists():
            return ["python3", str(script), query, cutoff]

        return None

    def _decide_dispatches(
        self,
        n_tools: int,
        tool_health: dict,
        pass_count: int,
    ) -> list[tuple[str, str]]:
        """Deterministic dispatch based on workspace state + tool health."""
        dispatches: list[tuple[str, str]] = []

        # Rule 1: No tools → always build tools first.
        if n_tools == 0:
            dispatches.append(("tool_builder", TOOL_BUILDER_SYSTEM))
            return dispatches

        # Rule 2: Tools exist but measured error rate > 30% → debug.
        if tool_health.get("error_rate", 0.0) > 0.3:
            dispatches.append(("debugger", DEBUGGER_SYSTEM))
            return dispatches

        # Rule 3: Tools work, score stagnant → strategist with escalation.
        if self._patience >= 1:
            tier_idx = min(self._patience - 1, len(ESCALATION_TIERS) - 1)
            tier_name, tier_prompt = ESCALATION_TIERS[tier_idx]
            dispatches.append((f"strategist_{tier_name}", tier_prompt))
            return dispatches

        # Rule 4: Tools work, score improving → refine.
        dispatches.append(("refiner", REFINER_SYSTEM))
        return dispatches
