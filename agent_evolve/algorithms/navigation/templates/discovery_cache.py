"""Discovery cache template — persistent shared memory across cycles.

Maintains ``infra/discovery_cache.jsonl`` with structured records of
API test results, tool test outcomes, and failure patterns. Each cycle,
agents read the cache before acting and append their discoveries after.

Addresses R1 (context fragmentation via persistent structured state)
using MLEvolve principle P1 (workspace as protocol) and P5 (structured
memory).

Activated via config: ``orchestrator: discovery_cache``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, seed_news_hint, no_throttle_rule

logger = logging.getLogger(__name__)

TOOL_BUILDER_SYSTEM = f"""\
You are a TOOL BUILDER with access to a shared discovery cache.

FIRST: read `infra/discovery_cache.jsonl` to see what APIs/tools have
already been tested. Do NOT re-test sources already marked as working
or failed — build on what's known.

THEN: build/fix tools based on the batch results and known-good sources.

{no_throttle_rule()}
{seed_news_hint()}

After building/testing tools, APPEND your discoveries to the cache:
```bash
echo '{{"cycle": N, "type": "tool_test", "tool": "name.py", "pass": true, "output_len": 500}}' >> infra/discovery_cache.jsonl
echo '{{"cycle": N, "type": "api_test", "source": "google_news_rss", "works": true, "latency_ms": 300}}' >> infra/discovery_cache.jsonl
```

Commit: `git add -A && git commit -m "tools: <summary>"`
"""

STRATEGY_WRITER_SYSTEM = """\
You are a STRATEGY WRITER with access to a shared discovery cache.

FIRST: read `infra/discovery_cache.jsonl` to see which tools work
and which sources are available. Also read `tools/registry.yaml`.

THEN: update `prompts/system.md` and create/update skills to teach
the solver how to use the KNOWN-GOOD tools effectively. Reference
specific tool names and their capabilities from the cache.

Do NOT modify tools/ — the tool builder handles that.
Do NOT add search count limits to the prompt.

Commit: `git add prompts/ skills/ && git commit -m "strategy: <summary>"`
"""


class Template(EvolutionTemplate):
    """Persistent discovery cache shared across agents and cycles."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "discovery_cache"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []
        mutated = False

        # Ensure cache file exists.
        cache_path = solver_workspace.root / "infra" / "discovery_cache.jsonl"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not cache_path.exists():
            cache_path.write_text("")

        # Count existing cache entries.
        cache_lines = [l for l in cache_path.read_text().splitlines() if l.strip()]
        trajectory.append({
            "step": "cache_state",
            "existing_entries": len(cache_lines),
            "cycle": evo_number,
        })

        # ── Tool builder (reads cache → builds tools → appends to cache) ──
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

        try:
            self.engine._run_llm(
                base_prompt, solver_workspace.root,
                system_prompt=TOOL_BUILDER_SYSTEM,
            )
            committed = vc.commit(
                message=f"evo-{evo_number}-tool-builder: cache-aware tools",
                tag=f"evo-{evo_number}-tool-builder",
            )
            trajectory.append({"step": "tool_builder", "mutated": committed})
            if committed:
                mutated = True
        except Exception as e:
            logger.warning("Tool builder failed: %s", e)
            trajectory.append({"step": "tool_builder", "mutated": False, "error": str(e)})

        # ── Strategy writer (reads cache → updates prompts/skills) ──
        try:
            self.engine._run_llm(
                base_prompt, solver_workspace.root,
                system_prompt=STRATEGY_WRITER_SYSTEM,
            )
            committed = vc.commit(
                message=f"evo-{evo_number}-strategy: cache-aware prompt",
                tag=f"evo-{evo_number}-strategy",
            )
            trajectory.append({"step": "strategy_writer", "mutated": committed})
            if committed:
                mutated = True
        except Exception as e:
            logger.warning("Strategy writer failed: %s", e)
            trajectory.append({"step": "strategy_writer", "mutated": False, "error": str(e)})

        # Count cache growth.
        new_lines = [l for l in cache_path.read_text().splitlines() if l.strip()]
        trajectory.append({
            "step": "cache_growth",
            "entries_before": len(cache_lines),
            "entries_after": len(new_lines),
        })

        # ── Guardrails G2-G5 ──
        if mutated:
            sample_query = "Bitcoin price January 2026"
            for r in batch_results[:3]:
                inp = r.get("task_input") or r.get("input") or ""
                if isinstance(inp, dict):
                    inp = inp.get("input", "")
                if inp:
                    sample_query = str(inp)[:100]
                    break
            guardrail_results = apply_all_guardrails(
                solver_workspace.root, sample_query=sample_query,
            )
            trajectory.append({"step": "guardrails", **guardrail_results})
            vc.commit(
                message=f"evo-{evo_number}-guardrails: cleanup",
                tag=f"evo-{evo_number}-guardrails",
            )

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
