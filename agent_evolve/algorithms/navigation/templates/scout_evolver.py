"""Scout-evolver template — API discovery → tool building.

Replaces the LLM planner with a **scout agent** that tests APIs in
the sandbox and writes structured ``discoveries.jsonl``. The evolver
then reads the discoveries and builds tools only for sources that
actually work — no rediscovery needed.

Addresses R1 (context fragmentation via structured file handoff) and
R2 (planner adds no signal → scout adds real signal).

Flow per cycle:
  1. Scout tests APIs in sandbox → writes infra/discoveries.jsonl
  2. Evolver reads discoveries + batch results → builds/fixes tools
  3. Guardrails G2-G5 applied post-evolution

Activated via config: ``orchestrator: scout_evolver``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, seed_news_hint, no_throttle_rule

logger = logging.getLogger(__name__)

SCOUT_SYSTEM = f"""\
You are an API SCOUT. Your job is to discover which data sources work
in this sandbox environment. You do NOT build tools — you only test
APIs and report results.

For each source below, run a real HTTP request and record whether it
works, its latency, and a sample of the response.

Sources to test (in priority order):
1. Google News RSS: `wget -q -O - "https://news.google.com/rss/search?q=Bitcoin+2026"`
2. Wikipedia API: `wget -q -O - "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Bitcoin&format=json"`
3. DuckDuckGo HTML: `wget -q -O - "https://html.duckduckgo.com/html/?q=Bitcoin+2026"`
4. Wayback Machine CDX: `wget -q -O - "https://web.archive.org/cdx/search/cdx?url=en.wikipedia.org&limit=3&output=json"`

For each, run the command with `workspace_bash` and record:
- source name
- works: true/false
- latency: approximate seconds
- sample: first 200 chars of output (or error message)

Write ALL results to `infra/discoveries.jsonl` (one JSON line per source):
```
{{"source": "google_news_rss", "works": true, "latency_s": 0.3, "sample": "..."}}
{{"source": "duckduckgo_html", "works": false, "error": "timeout after 8s"}}
```

Then commit: `git add infra/ && git commit -m "scout: API discovery"`
"""

EVOLVER_SYSTEM = f"""\
You are a TOOL BUILDER. You have access to infra/discoveries.jsonl
which tells you which APIs work in this sandbox.

Rules:
1. Read infra/discoveries.jsonl FIRST. Only build tools for sources
   marked "works": true.
2. {seed_news_hint()}
3. {no_throttle_rule()}
4. Test every tool you build: `python3 tools/<name>.py "query" "2026-01-15"`
5. Keep prompts/system.md under 10,000 characters.
6. Register all working tools in tools/registry.yaml.
7. Update prompts/system.md to teach the solver how to use each tool.

Commit: `git add -A && git commit -m "tools: <summary>"`
"""


class Template(EvolutionTemplate):
    """Scout discovers APIs → evolver builds tools from discoveries."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "scout_evolver"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []

        # ── Step 1: Scout — discover which APIs work ──
        logger.info("Scout: testing APIs in sandbox...")
        try:
            scout_result = self.engine._run_llm(
                "Test the APIs listed in your instructions. "
                "Write results to infra/discoveries.jsonl.",
                solver_workspace.root,
                system_prompt=SCOUT_SYSTEM,
            )
            vc.commit(
                message=f"evo-{evo_number}-scout: API discovery",
                tag=f"evo-{evo_number}-scout",
            )
            # Read discoveries
            disc_path = solver_workspace.root / "infra" / "discoveries.jsonl"
            discoveries = []
            if disc_path.exists():
                for line in disc_path.read_text().splitlines():
                    if line.strip():
                        try:
                            discoveries.append(json.loads(line))
                        except Exception:
                            pass
            n_working = sum(1 for d in discoveries if d.get("works"))
            trajectory.append({
                "step": "scout",
                "discoveries": len(discoveries),
                "working_sources": n_working,
            })
            logger.info("Scout found %d sources, %d working",
                        len(discoveries), n_working)
        except Exception as e:
            logger.warning("Scout failed: %s", e)
            trajectory.append({
                "step": "scout", "discoveries": 0, "error": str(e),
            })

        # ── Step 2: Evolver — build tools from discoveries ──
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
            evolver_result = self.engine._run_llm(
                base_prompt,
                solver_workspace.root,
                system_prompt=EVOLVER_SYSTEM,
            )
            mutated = True
            trajectory.append({
                "step": "evolve", "mutated": True,
            })
        except Exception as e:
            logger.warning("Evolver failed: %s", e)
            mutated = False
            trajectory.append({
                "step": "evolve", "mutated": False, "error": str(e),
            })

        committed = vc.commit(
            message=f"evo-{evo_number}-evolver: tool building",
            tag=f"evo-{evo_number}-evolver",
        )
        if not committed:
            mutated = False

        # ── Step 3: Guardrails G2-G5 ──
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
            trajectory.append({
                "step": "guardrails",
                **guardrail_results,
            })
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
