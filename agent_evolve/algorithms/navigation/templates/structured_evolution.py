"""Structured evolution template — 4-phase process-driven multi-agent.

Addresses all V1/V2 root causes (R1-R6) through a structured cycle:
  Phase 1: ANALYZE — read trajectories, update task board with failure regimes
  Phase 2: RESEARCH — parallel agents explore data source regimes
  Phase 3: BUILD — construct infra pipelines from verified research
  Phase 4: VERIFY — test pipelines, retry on failure (max 3)

Persists structured state across cycles via the evolution workspace
(task_board.md, research_log.jsonl, architecture.md).

Activated via config: ``orchestrator: structured_evolution``
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, no_throttle_rule
from ....engine.human_interface import create_interface
from ._evolution_workspace import (
    init_evolution_workspace,
    load_task_board,
    update_task_board,
    validate_task_board,
    load_research_log,
    append_research,
    validate_research_record,
    get_verified_approaches,
    load_architecture,
    update_architecture,
    append_insight,
    IGNORED_GAP_LABELS,
)

logger = logging.getLogger(__name__)


def _extract_sample_query(batch_results: list[dict]) -> str:
    for r in batch_results[:3]:
        inp = r.get("task_input") or r.get("input") or ""
        if isinstance(inp, dict):
            inp = inp.get("input", "")
        if inp:
            return str(inp)[:100]
    return "latest news headlines 2026"


def _load_hints(engine) -> str:
    """Load benchmark-specific hints from config."""
    hints_path = engine.config.extra.get("structured_evolution", {}).get(
        "benchmark_hints", ""
    )
    if hints_path:
        p = Path(hints_path)
        if p.exists():
            return p.read_text()
    return ""


def _parse_json_blocks(text: str) -> list[dict]:
    """Extract JSON objects from LLM output (one per line or in code blocks)."""
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except json.JSONDecodeError:
            pass
    return records


class Template(EvolutionTemplate):
    """4-phase structured evolution: analyze → research → build → verify."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "structured_evolution"

    def _call_llm_simple(self, prompt: str, system_prompt: str) -> str:
        """Call the LLM with no tools, no sandbox, no network.

        Used for the analyst phase which must be read-only. The prompt
        contains all needed context (trajectories, task board, research
        log) — the LLM just reasons and produces structured output.
        """
        cfg = self.engine.config
        try:
            from ....llm.bedrock import BedrockProvider
            if isinstance(self.engine.llm, BedrockProvider):
                response = self.engine.llm.converse_loop(
                    system_prompt=system_prompt,
                    user_message=prompt,
                    tools=[],
                    tool_executor={},
                    max_tokens=cfg.evolver_max_tokens,
                    temperature=0.0,
                    verbose=bool(cfg.extra.get("verbose")),
                )
                return response.content or ""
        except ImportError:
            pass
        return ""

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        se_config = cfg.extra.get("structured_evolution", {})
        research_k = se_config.get("research_parallel", 3)
        max_retries = se_config.get("build_verify_retries", 3)
        hitl_enabled = se_config.get("hitl_enabled", False)
        hints = _load_hints(self.engine)

        # Create human interface when HITL is enabled
        hi = None
        if hitl_enabled:
            hi = create_interface(cfg.extra)
            cfg.extra["human_in_the_loop"] = True

        ws_root = solver_workspace.root
        init_evolution_workspace(ws_root)

        trajectory: list[dict] = []

        # ── Phase 1: ANALYZE ──
        self._phase_analyze(
            vc, solver_workspace, batch_results,
            evo_number, hints, trajectory,
        )

        # ── Phase 2: RESEARCH ──
        self._phase_research(
            vc, solver_workspace, batch_results,
            evo_number, research_k, hints, trajectory,
        )

        # ── HITL: handle credential-gated research records ──
        if hi:
            self._hitl_credentials(ws_root, evo_number, hi, hints, trajectory)

        # ── HITL: show task board to human before build ──
        if hi:
            self._hitl_task_board(ws_root, hi, trajectory)

        # ── Phase 3+4: BUILD + VERIFY loop ──
        mutated = self._phase_build_verify(
            vc, solver_workspace, batch_results,
            evo_number, max_retries, hints, trajectory,
        )

        # ── Guardrails G2-G5 ──
        if mutated:
            sample_query = _extract_sample_query(batch_results)
            guardrail_results = apply_all_guardrails(
                ws_root, sample_query=sample_query,
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

    # ────────────────────────────────────────────────────────────────
    # Phase 1: Analyze
    # ────────────────────────────────────────────────────────────────

    def _phase_analyze(
        self, vc, solver_workspace, batch_results,
        evo_number, hints, trajectory,
    ):
        from ....algorithms.aevolve.prompts import build_evolution_prompt
        cfg = self.engine.config
        ws_root = solver_workspace.root

        task_board = load_task_board(ws_root)
        research_log = load_research_log(ws_root)

        base_prompt = build_evolution_prompt(
            solver_workspace, batch_results, drafts=[],
            evo_number=evo_number,
            evolve_prompts=cfg.evolve_prompts,
            evolve_skills=cfg.evolve_skills,
            evolve_memory=cfg.evolve_memory,
            evolve_tools=cfg.evolve_tools,
            evolve_infra=cfg.evolve_infra,
        )

        analyst_prompt = (
            f"ROLE: You are a failure analyst for evolution cycle {evo_number}.\n\n"
            f"BATCH TRAJECTORIES:\n{base_prompt}\n\n"
            f"CURRENT TASK BOARD:\n{task_board}\n\n"
            f"RESEARCH LOG ({len(research_log)} records):\n"
            + "\n".join(json.dumps(r) for r in research_log[-20:])
            + "\n\n"
            "OUTPUT FORMAT (you MUST use this exact structure):\n"
            "## Failure Patterns (Cycle N)\n"
            "- <regime_tag>: <count> tasks fail because <reason>. PRIORITY: HIGH|MEDIUM|LOW\n"
            "(one bullet per regime)\n\n"
            "## Verified Capabilities\n"
            "- <approach>: <what it covers> (cycle N)\n\n"
            "## Unresolved\n"
            "- <regime>: <why stuck> (cycle N)\n\n"
            "## Human Requests\n"
            "- (none this cycle)\n\n"
            "INSTRUCTIONS:\n"
            "1. Identify failure patterns grouped by capability regime.\n"
            "2. Assign priority (HIGH/MEDIUM/LOW) based on task count.\n"
            "3. Cross-reference with the research log.\n"
            "4. Output ONLY the task board content in the format above.\n"
            "5. Do NOT include conversational text, explanations, or tables.\n"
            "6. Do NOT suggest solutions. Diagnosis only.\n"
        )
        if hints:
            analyst_prompt += f"\nBENCHMARK HINTS:\n{hints}\n"

        system = (
            "You are a failure analyst. Output ONLY the task board in the "
            "exact markdown format specified. No conversational text."
        )

        logger.info("Phase 1: Analyzing batch failures (no-tools)...")
        try:
            content = self._call_llm_simple(analyst_prompt, system)
            if content.strip() and validate_task_board(content):
                update_task_board(ws_root, content)
                vc.commit(
                    message=f"evo-{evo_number}-analyze: update task board",
                    tag=f"evo-{evo_number}-analyze",
                )
                trajectory.append({"step": "analyze", "success": True})
            elif content.strip():
                # Retry with repair prompt
                repair_prompt = (
                    "Your previous output was not in the correct format.\n"
                    "Rewrite it using EXACTLY this structure:\n\n"
                    "## Failure Patterns (Cycle N)\n"
                    "- <regime_tag>: <count> tasks fail because <reason>. "
                    "PRIORITY: HIGH|MEDIUM|LOW\n\n"
                    "## Verified Capabilities\n\n"
                    "## Unresolved\n\n"
                    "## Human Requests\n\n"
                    f"Here is what you wrote:\n{content[:2000]}\n"
                )
                repaired = self._call_llm_simple(repair_prompt, system)
                if repaired.strip() and validate_task_board(repaired):
                    update_task_board(ws_root, repaired)
                    vc.commit(
                        message=f"evo-{evo_number}-analyze: update task board (repaired)",
                        tag=f"evo-{evo_number}-analyze",
                    )
                    trajectory.append({"step": "analyze", "success": True, "repaired": True})
                else:
                    logger.warning("Phase 1: analyst output failed validation after repair")
                    trajectory.append({"step": "analyze", "success": False, "reason": "invalid_format"})
            else:
                trajectory.append({"step": "analyze", "success": False, "reason": "empty_output"})
        except Exception as e:
            logger.warning("Phase 1 (analyze) failed: %s", e)
            trajectory.append({"step": "analyze", "success": False, "error": str(e)})

    # ────────────────────────────────────────────────────────────────
    # Phase 2: Research
    # ────────────────────────────────────────────────────────────────

    def _phase_research(
        self, vc, solver_workspace, batch_results,
        evo_number, research_k, hints, trajectory,
    ):
        ws_root = solver_workspace.root
        task_board = load_task_board(ws_root)

        gaps = self._extract_gaps(task_board, research_k)
        if not gaps:
            logger.info("Phase 2: No gaps to research.")
            trajectory.append({"step": "research", "gaps": 0})
            return

        logger.info("Phase 2: Researching %d gaps...", len(gaps))

        known = load_research_log(ws_root)
        known_summary = "\n".join(
            f"- {r['approach']}: works={r['works']}" for r in known[-30:]
        )

        def _research_one(gap: str) -> dict:
            prompt = (
                f"REGIME TO INVESTIGATE: {gap}\n\n"
                f"ALREADY TESTED (from research_log):\n{known_summary}\n\n"
                "INSTRUCTIONS:\n"
                "1. Test MULTIPLE approaches for this regime in the sandbox.\n"
                "2. For each, make a real HTTP request or test command.\n"
                "3. Record EXACTLY what you called, what came back, "
                "whether it's usable.\n"
                "4. Output ONE JSON record per line for each test with ALL fields:\n"
                '{"cycle": ' + str(evo_number) + ', "regime": "' + gap + '", '
                '"approach": "<name>", "endpoint": "<url or command>", '
                '"tested": true, "works": true/false, '
                '"latency_ms": <number>, '
                '"coverage": ["<subtypes handled>"], '
                '"does_not_cover": ["<subtypes it fails on>"], '
                '"complementary_to": ["<other approach>"], '
                '"sample_output": "<first lines of output>", '
                '"credential_needed": false, "credential_env": "", '
                '"error": "", "notes": "<usage tips>"}\n'
                "5. Test at least 2-3 different approaches per regime.\n"
            )
            if hints:
                prompt += f"\nBENCHMARK HINTS:\n{hints}\n"

            system = (
                f"You are a research agent investigating: {gap}\n"
                "Test approaches with real HTTP calls in the sandbox. "
                "Output structured JSON records, one per line."
            )
            try:
                result = self.engine._run_llm(
                    prompt, ws_root, system_prompt=system,
                )
                records = _parse_json_blocks(result.get("content", ""))
                saved = 0
                for r in records:
                    r.setdefault("cycle", evo_number)
                    r.setdefault("regime", gap)
                    r.setdefault("tested", True)
                    if validate_research_record(r):
                        append_research(ws_root, r)
                        saved += 1
                return {"gap": gap, "records": saved}
            except Exception as e:
                logger.warning("Research for %s failed: %s", gap, e)
                return {"gap": gap, "records": 0, "error": str(e)}

        results = []
        with ThreadPoolExecutor(max_workers=min(research_k, 3)) as pool:
            futures = {pool.submit(_research_one, g): g for g in gaps}
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({"gap": futures[fut], "error": str(e)})

        vc.commit(
            message=f"evo-{evo_number}-research: {len(gaps)} regimes",
            tag=f"evo-{evo_number}-research",
        )
        trajectory.append({
            "step": "research",
            "gaps": len(gaps),
            "results": results,
        })

    def _extract_gaps(self, task_board: str, k: int) -> list[str]:
        """Extract top-K priority gaps from validated failure-pattern bullets.

        Only parses lines matching the planned format:
          - <regime_tag>: ... PRIORITY: HIGH|MEDIUM|LOW
        Ignores table rows, generic labels, and conversational text.
        """
        in_failure_section = False
        gaps = []
        for line in task_board.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("## failure pattern"):
                in_failure_section = True
                continue
            if stripped.startswith("## "):
                in_failure_section = False
                continue
            if not in_failure_section:
                continue
            if "|" in stripped:
                continue
            match = re.match(
                r"[-*]\s*(\w[\w_]*):\s*\d+.*PRIORITY:\s*(HIGH|MEDIUM|LOW)",
                stripped, re.IGNORECASE,
            )
            if match:
                tag = match.group(1).lower()
                if tag not in IGNORED_GAP_LABELS:
                    gaps.append(tag)
        return gaps[:k]

    # ────────────────────────────────────────────────────────────────
    # HITL integration
    # ────────────────────────────────────────────────────────────────

    def _hitl_credentials(self, ws_root, evo_number, hi, hints, trajectory):
        """Handle credential-gated research records via human interface.

        After the human supplies a credential, reruns research for that
        regime once and appends a real source-test record.
        """
        records = load_research_log(ws_root)
        pending = [
            r for r in records
            if r.get("credential_needed") and r.get("works") in ("unknown", "blocked")
        ]
        if not pending:
            return

        retested = 0
        for rec in pending:
            env_var = rec.get("credential_env", "API_KEY")
            approach = rec.get("approach", "unknown")
            regime = rec.get("regime", "unknown")
            endpoint = rec.get("endpoint", "")
            response = hi.handle(
                f"Research found '{approach}' for regime '{regime}' but needs "
                f"credentials. Provide {env_var} or type 'skip':",
                action_type="credential_request",
            )
            if response.strip().lower() in ("skip", "(no response)", ""):
                append_research(ws_root, {
                    "cycle": evo_number, "regime": regime,
                    "approach": approach, "endpoint": endpoint,
                    "tested": False, "works": False,
                    "latency_ms": 0, "coverage": [], "does_not_cover": [],
                    "complementary_to": [], "sample_output": "",
                    "credential_needed": True, "credential_env": env_var,
                    "error": "Human skipped credential", "notes": "",
                })
            else:
                import os
                os.environ[env_var] = response.strip()
                # Rerun research for this specific regime+approach
                retest_result = self._retest_credential_approach(
                    ws_root, evo_number, regime, approach, endpoint,
                    env_var, hints,
                )
                retested += 1
                trajectory_note = retest_result

        trajectory.append({
            "step": "hitl_credentials",
            "pending": len(pending),
            "retested": retested,
        })

    def _retest_credential_approach(
        self, ws_root, evo_number, regime, approach, endpoint, env_var, hints,
    ) -> dict:
        """Rerun research for a credential-gated approach after credential supplied."""
        prompt = (
            f"RETEST: The credential {env_var} has been supplied.\n"
            f"Test the approach '{approach}' for regime '{regime}'.\n"
            f"Endpoint: {endpoint}\n\n"
            "Run the test in the sandbox and output ONE JSON record:\n"
            f'{{"cycle": {evo_number}, "regime": "{regime}", '
            f'"approach": "{approach}", "endpoint": "{endpoint}", '
            '"tested": true, "works": true/false, "latency_ms": <ms>, '
            '"coverage": [...], "does_not_cover": [...], '
            '"complementary_to": [...], "sample_output": "...", '
            f'"credential_needed": true, "credential_env": "{env_var}", '
            '"error": "", "notes": "..."}\n'
        )
        if hints:
            prompt += f"\nBENCHMARK HINTS:\n{hints}\n"

        system = (
            f"You are a research agent retesting '{approach}' for regime "
            f"'{regime}' after credentials were supplied. Test with real "
            "HTTP calls and report the result as a JSON record."
        )

        try:
            result = self.engine._run_llm(prompt, ws_root, system_prompt=system)
            parsed = _parse_json_blocks(result.get("content", ""))
            if parsed:
                rec = parsed[0]
                rec.setdefault("cycle", evo_number)
                rec.setdefault("regime", regime)
                rec.setdefault("approach", approach)
                rec.setdefault("tested", True)
                rec.setdefault("credential_needed", True)
                rec.setdefault("credential_env", env_var)
                if validate_research_record(rec):
                    append_research(ws_root, rec)
                    return {"retested": True, "works": rec.get("works")}
            # Fallback: no parseable record
            append_research(ws_root, {
                "cycle": evo_number, "regime": regime,
                "approach": approach, "endpoint": endpoint,
                "tested": True, "works": False,
                "latency_ms": 0, "coverage": [], "does_not_cover": [],
                "complementary_to": [], "sample_output": "",
                "credential_needed": True, "credential_env": env_var,
                "error": "Retest produced no parseable record", "notes": "",
            })
            return {"retested": True, "works": False}
        except Exception as e:
            append_research(ws_root, {
                "cycle": evo_number, "regime": regime,
                "approach": approach, "endpoint": endpoint,
                "tested": True, "works": False,
                "latency_ms": 0, "coverage": [], "does_not_cover": [],
                "complementary_to": [], "sample_output": "",
                "credential_needed": True, "credential_env": env_var,
                "error": str(e), "notes": "",
            })
            return {"retested": True, "works": False, "error": str(e)}

    def _hitl_task_board(self, ws_root, hi, trajectory):
        """Show task board to human and accept edits before build."""
        board = load_task_board(ws_root)
        response = hi.handle(
            f"Current task board before build phase:\n\n{board}\n\n"
            "Add requests or adjustments (or press Enter to skip):",
            action_type="task_board_review",
        )
        if response.strip() and response.strip() not in ("(no response)", "skip"):
            board += f"\n\n## Human Requests\n- {response.strip()}\n"
            update_task_board(ws_root, board)
            trajectory.append({"step": "hitl_task_board", "updated": True})
        else:
            trajectory.append({"step": "hitl_task_board", "updated": False})

    # ────────────────────────────────────────────────────────────────
    # Phase 3+4: Build + Verify loop
    # ────────────────────────────────────────────────────────────────

    def _phase_build_verify(
        self, vc, solver_workspace, batch_results,
        evo_number, max_retries, hints, trajectory,
    ) -> bool:
        ws_root = solver_workspace.root
        verified = get_verified_approaches(ws_root)
        if not verified:
            logger.info("Phase 3: No verified approaches to build from.")
            trajectory.append({"step": "build", "mutated": False, "reason": "no_verified"})
            return False

        architecture = load_architecture(ws_root)
        task_board = load_task_board(ws_root)

        verified_summary = "\n".join(
            json.dumps(r) for r in verified[-30:]
        )

        builder_system = (
            f"You are an infrastructure builder for evolution cycle {evo_number}.\n\n"
            f"RULES:\n"
            f"1. Only build from VERIFIED research results (works: true).\n"
            f"2. {no_throttle_rule()}\n"
            "3. Build class-based pipelines under infra/<regime>_pipeline.py.\n"
            "4. Each pipeline has execute(query, **context) -> str.\n"
            "5. Source chains ordered by coverage breadth + reliability.\n"
            "6. Keep prompts/system.md under 10,000 characters.\n"
            "7. Update architecture.md with what you built and why.\n"
            "8. Design for regime generalization, not specific instances.\n"
            "9. Also write tools and update tools/registry.yaml.\n"
            "10. Commit with: git add -A && git commit -m 'build: <summary>'\n"
        )
        if hints:
            builder_system += f"\nBENCHMARK HINTS:\n{hints}\n"

        builder_prompt = (
            f"VERIFIED RESEARCH RESULTS:\n{verified_summary}\n\n"
            f"TASK BOARD:\n{task_board}\n\n"
            f"CURRENT ARCHITECTURE:\n{architecture}\n\n"
            "Build infra pipelines and tools from the verified research. "
            "Update prompts/system.md to teach the solver how to use them."
        )

        # Tag the pre-build state so we can roll back on failure
        pre_build_tag = f"evo-{evo_number}-pre-build"
        vc.commit(message="pre-build checkpoint", tag=pre_build_tag)

        mutated = False
        for attempt in range(1, max_retries + 1):
            logger.info("Phase 3-4: Build attempt %d/%d", attempt, max_retries)

            # BUILD
            try:
                self.engine._run_llm(
                    builder_prompt, ws_root, system_prompt=builder_system,
                )
                committed = vc.commit(
                    message=f"evo-{evo_number}-build-attempt-{attempt}",
                    tag=f"evo-{evo_number}-build-{attempt}",
                )
                trajectory.append({
                    "step": "build", "attempt": attempt,
                    "mutated": committed,
                })
                if not committed:
                    break
            except Exception as e:
                logger.warning("Build attempt %d failed: %s", attempt, e)
                trajectory.append({
                    "step": "build", "attempt": attempt,
                    "mutated": False, "error": str(e),
                })
                break

            # VERIFY
            verify_result = self._verify(
                vc, solver_workspace, batch_results, evo_number, attempt,
            )
            trajectory.append({
                "step": "verify", "attempt": attempt, **verify_result,
            })

            if verify_result.get("passed", False):
                append_research(ws_root, {
                    "cycle": evo_number, "regime": "all",
                    "approach": "build_output", "tested": True,
                    "works": True, "type": "tool_test",
                    "evidence": verify_result.get("report", "")[:300],
                })
                mutated = True
                break

            # Roll back to pre-build state before retry
            vc.rollback_to_tag(pre_build_tag)

            if attempt < max_retries:
                builder_prompt = (
                    f"PREVIOUS BUILD FAILED VERIFICATION (attempt {attempt}).\n\n"
                    f"VERIFICATION REPORT:\n{verify_result.get('report', 'unknown')}\n\n"
                    f"VERIFIED RESEARCH:\n{verified_summary}\n\n"
                    "Fix the issues and rebuild. Focus on what the verifier reported."
                )

        if not mutated:
            # Ensure workspace is clean — roll back to pre-build
            vc.rollback_to_tag(pre_build_tag)
            append_research(ws_root, {
                "cycle": evo_number, "regime": "all",
                "approach": "build_output", "tested": True,
                "works": False, "type": "tool_test",
                "error": "All build-verify attempts exhausted",
            })
            trajectory.append({
                "step": "build_verify_exhausted",
                "attempts": max_retries,
            })

        return mutated

    def _verify(
        self, vc, solver_workspace, batch_results,
        evo_number, attempt,
    ) -> dict[str, Any]:
        """Run verifier agent on the current workspace."""
        ws_root = solver_workspace.root
        sample_query = _extract_sample_query(batch_results)

        verifier_system = (
            "You are a verification agent. Test each new tool and infra pipeline.\n\n"
            "For each tool, run 3 tests:\n"
            "1. A realistic query from the batch tasks\n"
            "2. An edge case (very old date, unusual characters)\n"
            "3. An error case (empty query, invalid input)\n\n"
            "For each test, evaluate:\n"
            "- Does it return data? (not just 'No results')\n"
            "- Is the data plausible?\n"
            "- Does date filtering work?\n\n"
            "Output a verification report:\n"
            "VERDICT: PASS or FAIL\n"
            "Then list each tool/pipeline tested with its result.\n"
        )

        verifier_prompt = (
            f"Test the tools and infra pipelines in this workspace.\n"
            f"Sample query to use: {sample_query}\n"
            f"Sample cutoff date: 2026-01-15\n"
        )

        try:
            result = self.engine._run_llm(
                verifier_prompt, ws_root, system_prompt=verifier_system,
            )
            content = result.get("content", "")
            passed = "VERDICT: PASS" in content.upper() or "PASS" in content.upper().split("\n")[0] if content else False
            vc.commit(
                message=f"evo-{evo_number}-verify-{attempt}",
                tag=f"evo-{evo_number}-verify-{attempt}",
            )
            return {"passed": passed, "report": content[:500]}
        except Exception as e:
            logger.warning("Verification failed: %s", e)
            return {"passed": False, "report": str(e)}
