"""Population template — N parallel evolvers with tournament + fusion.

Runs N independent evolver attempts with different seed prompts, then
selects the best workspace via a deterministic tournament (tool count
+ registry health) and fuses non-overlapping tools from runners-up.

Addresses R1 (diversity compensates for context fragmentation) using
MLEvolve principle P5 (fusion over selection).

Activated via config: ``orchestrator: population``
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, seed_news_hint, no_throttle_rule

logger = logging.getLogger(__name__)

POPULATION_SIZE = 3

SEED_VARIATIONS = [
    f"Start by building `news_search.py` using Google News RSS.\n{no_throttle_rule()}\n{seed_news_hint()}",
    f"Start by building `wiki_search.py` using the Wikipedia API revision endpoint.\n{no_throttle_rule()}",
    f"Start by building `prediction_market.py` using Manifold Markets API.\n{no_throttle_rule()}",
]


class Template(EvolutionTemplate):
    """N parallel evolvers → tournament → fusion."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "population"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []

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

        # ── Phase 1: Run N independent evolvers ──
        pop_dir = Path(tempfile.mkdtemp(prefix="population-"))
        candidates: list[dict] = []

        for i in range(min(POPULATION_SIZE, len(SEED_VARIATIONS))):
            candidate_dir = pop_dir / f"candidate_{i}"
            shutil.copytree(solver_workspace.root, candidate_dir,
                            dirs_exist_ok=True)

            seed = SEED_VARIATIONS[i]
            try:
                self.engine._run_llm(
                    base_prompt, candidate_dir,
                    system_prompt=seed,
                )
                # Score: count working tools in registry
                reg_path = candidate_dir / "tools" / "registry.yaml"
                tools = []
                if reg_path.exists():
                    try:
                        data = yaml.safe_load(reg_path.read_text()) or {}
                        tools = data.get("tools", [])
                    except Exception:
                        pass
                n_tools = len(tools)
                tool_names = [t.get("name", "") for t in tools]

                candidates.append({
                    "index": i,
                    "dir": str(candidate_dir),
                    "n_tools": n_tools,
                    "tool_names": tool_names,
                    "seed_hint": seed[:50],
                })
                trajectory.append({
                    "step": "candidate",
                    "index": i,
                    "n_tools": n_tools,
                    "tool_names": tool_names,
                })
                logger.info("Candidate %d: %d tools (%s)",
                            i, n_tools, tool_names)
            except Exception as e:
                logger.warning("Candidate %d failed: %s", i, e)
                candidates.append({
                    "index": i, "dir": str(candidate_dir),
                    "n_tools": 0, "tool_names": [], "error": str(e),
                })
                trajectory.append({
                    "step": "candidate", "index": i,
                    "n_tools": 0, "error": str(e),
                })

        if not candidates:
            trajectory.append({"step": "tournament", "winner": None})
            shutil.rmtree(pop_dir, ignore_errors=True)
            return {
                "evo_number": evo_number, "mutated": False,
                "plan": {}, "branches": tree.branch_names(),
                "trajectory": trajectory,
            }

        # ── Phase 2: Tournament — pick candidate with most tools ──
        winner = max(candidates, key=lambda c: c["n_tools"])
        runners_up = [c for c in candidates if c["index"] != winner["index"]]
        trajectory.append({
            "step": "tournament",
            "winner_index": winner["index"],
            "winner_tools": winner["tool_names"],
            "runners_up": [r["index"] for r in runners_up],
        })
        logger.info("Tournament winner: candidate %d (%d tools)",
                     winner["index"], winner["n_tools"])

        # ── Phase 3: Copy winner back to solver workspace ──
        winner_dir = Path(winner["dir"])
        for subdir in ("tools", "prompts", "skills", "memory"):
            src = winner_dir / subdir
            dst = solver_workspace.root / subdir
            if src.exists():
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # ── Phase 4: Fuse non-overlapping tools from runners-up ──
        winner_tool_names = set(winner.get("tool_names", []))
        fused_tools = []
        for runner in runners_up:
            runner_dir = Path(runner["dir"])
            for tool_name in runner.get("tool_names", []):
                if tool_name not in winner_tool_names:
                    src_script = runner_dir / "tools" / f"{tool_name}.py"
                    dst_script = solver_workspace.root / "tools" / f"{tool_name}.py"
                    if src_script.exists() and not dst_script.exists():
                        shutil.copy2(src_script, dst_script)
                        fused_tools.append(tool_name)
                        winner_tool_names.add(tool_name)

        # Update registry with fused tools.
        if fused_tools:
            reg_path = solver_workspace.root / "tools" / "registry.yaml"
            try:
                data = yaml.safe_load(reg_path.read_text()) or {}
                existing = data.get("tools", [])
                for name in fused_tools:
                    existing.append({"name": name, "description": f"fused from runner-up"})
                data["tools"] = existing
                reg_path.write_text(yaml.dump(data, default_flow_style=False))
            except Exception:
                pass

        trajectory.append({
            "step": "fusion",
            "fused_tools": fused_tools,
            "total_tools": len(winner_tool_names),
        })
        logger.info("Fusion: added %d tools from runners-up: %s",
                     len(fused_tools), fused_tools)

        # ── Phase 5: Guardrails G2-G5 ──
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

        # Commit everything.
        committed = vc.commit(
            message=f"evo-{evo_number}-population: winner={winner['index']}+fusion",
            tag=f"evo-{evo_number}-population",
        )

        # Cleanup temp dirs.
        shutil.rmtree(pop_dir, ignore_errors=True)

        return {
            "evo_number": evo_number,
            "mutated": committed,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
