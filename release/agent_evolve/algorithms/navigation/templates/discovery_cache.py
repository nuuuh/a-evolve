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


def load_cache(path: Path) -> list[dict]:
    """Load all records from the discovery cache."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return records


CACHE_SCHEMA_FIELDS = {"cycle", "type", "source", "works", "latency_ms", "sample", "error"}


def normalize_cache_record(record: dict) -> dict:
    """Ensure a record has all 7 required fields with correct defaults."""
    return {
        "cycle": record.get("cycle", 0),
        "type": record.get("type", "unknown"),
        "source": record.get("source") or record.get("tool") or "",
        "works": record.get("works") if "works" in record else record.get("pass", False),
        "latency_ms": record.get("latency_ms", 0),
        "sample": record.get("sample", ""),
        "error": record.get("error", ""),
    }


def validate_cache_record(record: dict) -> bool:
    """Check a record has all required schema fields with correct types."""
    if not CACHE_SCHEMA_FIELDS.issubset(record.keys()):
        return False
    if not isinstance(record["cycle"], (int, float)):
        return False
    if not isinstance(record["type"], str):
        return False
    return True


def append_cache_record(path: Path, record: dict) -> None:
    """Normalize, validate, and append a record to the cache."""
    normalized = normalize_cache_record(record)
    if not validate_cache_record(normalized):
        raise ValueError(f"Invalid cache record: {normalized}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(normalized, default=str) + "\n")


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

        cache_path = solver_workspace.root / "infra" / "discovery_cache.jsonl"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing cache.
        existing = load_cache(cache_path)
        append_cache_record(cache_path, {
            "cycle": evo_number, "type": "cycle_start",
            "existing_entries": len(existing),
        })
        trajectory.append({
            "step": "cache_state",
            "existing_entries": len(existing),
            "cycle": evo_number,
        })

        # Build known-good/known-failed summary from cache for prompts.
        good_sources = [r.get("source", "") for r in existing
                        if r.get("type") == "api_test" and r.get("works")]
        failed_sources = [r.get("source", "") for r in existing
                         if r.get("type") == "api_test" and not r.get("works")]
        cache_summary = ""
        if good_sources:
            cache_summary += f"Known-good sources: {', '.join(good_sources)}\n"
        if failed_sources:
            cache_summary += f"Known-failed sources: {', '.join(failed_sources)}\n"

        # ── Tool builder ──
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

        tool_builder_prompt = TOOL_BUILDER_SYSTEM
        if cache_summary:
            tool_builder_prompt += f"\n## Known Sources from Cache\n{cache_summary}"

        try:
            self.engine._run_llm(
                base_prompt, solver_workspace.root,
                system_prompt=tool_builder_prompt,
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

        # Programmatically test each tool and append results to cache.
        from ._guardrails import verify_tools
        sample_query = "Bitcoin price January 2026"
        for r in batch_results[:3]:
            inp = r.get("task_input") or r.get("input") or ""
            if isinstance(inp, dict):
                inp = inp.get("input", "")
            if inp:
                sample_query = str(inp)[:100]
                break

        import yaml as _yaml
        reg_path = solver_workspace.root / "tools" / "registry.yaml"
        if reg_path.exists():
            try:
                reg_data = _yaml.safe_load(reg_path.read_text()) or {}
                for t in reg_data.get("tools", []):
                    name = t.get("name", "")
                    script = solver_workspace.root / "tools" / f"{name}.py"
                    import subprocess
                    passed = False
                    error_msg = ""
                    if script.exists():
                        try:
                            proc = subprocess.run(
                                ["python3", str(script), sample_query, "2026-01-15"],
                                capture_output=True, text=True, timeout=15,
                                cwd=str(solver_workspace.root),
                            )
                            passed = proc.returncode == 0 and bool(proc.stdout.strip())
                            if not passed:
                                error_msg = (proc.stderr or "empty output")[:100]
                        except subprocess.TimeoutExpired:
                            error_msg = "timeout"
                        except Exception as e:
                            error_msg = str(e)[:100]
                    else:
                        error_msg = "script missing"
                    append_cache_record(cache_path, {
                        "cycle": evo_number, "type": "tool_test",
                        "tool": name, "pass": passed,
                        "error": error_msg if not passed else "",
                    })
            except Exception:
                pass

        # ── Strategy writer ──
        strategy_prompt = STRATEGY_WRITER_SYSTEM
        if cache_summary:
            strategy_prompt += f"\n## Known Sources from Cache\n{cache_summary}"

        try:
            self.engine._run_llm(
                base_prompt, solver_workspace.root,
                system_prompt=strategy_prompt,
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
        final_cache = load_cache(cache_path)
        trajectory.append({
            "step": "cache_growth",
            "entries_before": len(existing),
            "entries_after": len(final_cache),
            "new_records": len(final_cache) - len(existing),
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
