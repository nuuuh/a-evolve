"""GEPA-lite — reflective prompt evolution, prompts-only edit surface.

Fair-comparison port of GEPA (Agarwal et al., NeurIPS 2025). Preserves the
reflect-then-mutate loop and prompt-only framing; drops the Pareto archive
because our benchmarks provide trajectory-only feedback during evolution
(the observer strips scalar scores before templates see batch_results).

Two-phase cycle per evolution:
  Phase 1 (reflect): no-tools LLM call reads trajectories + current prompt,
                     writes a textual critique to evolver_workspace.
  Phase 2 (mutate):  bash-enabled LLM call rewrites prompts/system.md based
                     on the critique. Out-of-scope edits are reverted.

Activated via config: ``orchestrator: gepa_lite``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._evolution_workspace import (
    get_evolver_workspace_path,
    init_evolution_workspace,
)

logger = logging.getLogger(__name__)

_GENERAL_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(prompts_dir: Path | None, name: str, fallback: str = "") -> str:
    """Load a general prompt and merge benchmark-specific context.

    Same pattern as structured_evolution._load_prompt: the general prompt
    under templates/prompts/<name> contains a ``{benchmark_context}``
    placeholder which is replaced with content from <prompts_dir>/<name>
    if it exists, otherwise with an empty string.
    """
    general = _GENERAL_PROMPTS_DIR / name
    if general.exists():
        text = general.read_text()
    elif fallback:
        text = fallback
    else:
        return ""

    benchmark_context = ""
    if prompts_dir:
        bp = Path(prompts_dir) / name
        if bp.exists():
            benchmark_context = bp.read_text().strip()
    return text.replace("{benchmark_context}", benchmark_context)


def _summarize_batch(batch_results: list[dict], max_chars: int = 16000) -> str:
    """Render a concise per-task summary of trajectories for the reflector.

    Reveal-gate aware: records whose ``success`` has been stripped by the
    observer are labeled "pending reveal" rather than "failed".
    """
    lines = []
    budget = max_chars
    for r in batch_results:
        tid = r.get("instance_id", "?")
        if "success" in r:
            status = "PASS" if r.get("success") else "FAIL"
        else:
            status = "PENDING"
        turns = r.get("turns", "?")
        task_in = str(r.get("task_input") or r.get("input") or "")[:400]
        conv = r.get("conversation") or []
        tail = ""
        if conv:
            try:
                last = conv[-1]
                if isinstance(last, dict):
                    tail = json.dumps(last)[:600]
                else:
                    tail = str(last)[:600]
            except Exception:
                tail = ""
        block = (
            f"### task={tid} status={status} turns={turns}\n"
            f"input: {task_in}\n"
            f"last_turn: {tail}\n"
        )
        if len(block) > budget:
            lines.append(f"### ...({len(batch_results) - len(lines)} more tasks truncated)")
            break
        lines.append(block)
        budget -= len(block)
    return "\n".join(lines)


def _load_recent_reflections(evo_ws: Path, k: int = 3) -> str:
    """Return the k most recent reflection files, concatenated."""
    files = sorted(evo_ws.glob("reflection_*.md"))
    if not files:
        return "(no prior reflections)"
    chunks = []
    for f in files[-k:]:
        chunks.append(f"## {f.name}\n{f.read_text().strip()[:4000]}")
    return "\n\n".join(chunks)


class Template(EvolutionTemplate):
    """Reflect → Mutate, restricted to prompts/system.md."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "gepa_lite"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        gl_config = cfg.extra.get("gepa_lite", {})
        prompts_dir_str = gl_config.get("prompts_dir", "")
        prompts_dir = Path(prompts_dir_str) if prompts_dir_str else None
        k_recent = int(gl_config.get("recent_reflections", 3))

        ws_root = solver_workspace.root
        evo_ws = get_evolver_workspace_path(ws_root)
        init_evolution_workspace(evo_ws)

        trajectory: list[dict] = []

        # ── Phase 1: Reflect ──────────────────────────────────────
        system_md = ws_root / "prompts" / "system.md"
        current_prompt = system_md.read_text() if system_md.exists() else "(no system.md)"
        prior_refl = _load_recent_reflections(evo_ws, k=k_recent)
        batch_summary = _summarize_batch(batch_results)

        reflect_prompt = _load_prompt(
            prompts_dir, "gepa_reflect.md", "Reflect on the batch.",
        ).format(
            evo_number=evo_number,
            current_prompt=current_prompt,
            prior_reflections=prior_refl,
            batch=batch_summary,
        )
        reflect_system = _load_prompt(
            prompts_dir, "gepa_reflect_system.md", "You are a reflective analyst.",
        )

        logger.info("GEPA-lite Phase 1: Reflecting on batch (cycle %d)...", evo_number)
        critique = ""
        try:
            result = self.engine._run_llm(
                reflect_prompt, ws_root,
                system_prompt=reflect_system,
                evolver_workspace=evo_ws,
            )
            critique = (result.get("content") or "").strip()
        except Exception as e:
            logger.warning("Phase 1 (reflect) failed: %s", e)
            trajectory.append({"step": "reflect", "success": False, "error": str(e)})

        if critique:
            (evo_ws / f"reflection_{evo_number:03d}.md").write_text(critique)
            vc.commit(
                message=f"evo-{evo_number}-gepa-reflect: critique written",
                tag=f"evo-{evo_number}-reflect",
            )
            trajectory.append({
                "step": "reflect", "success": True, "chars": len(critique),
            })
        else:
            trajectory.append({"step": "reflect", "success": False,
                               "reason": "empty_critique"})
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # ── Phase 2: Mutate (scoped to prompts/system.md) ────────
        pre_mutate_tag = f"evo-{evo_number}-pre-mutate"
        vc.commit(
            message=f"evo-{evo_number} pre-mutate checkpoint",
            tag=pre_mutate_tag,
        )

        mutate_prompt = _load_prompt(
            prompts_dir, "gepa_mutate.md", "Rewrite prompts/system.md.",
        ).format(
            evo_number=evo_number,
            critique=critique[:8000],
            current_prompt=current_prompt,
        )
        mutate_system = _load_prompt(
            prompts_dir, "gepa_mutate_system.md", "Prompt editor.",
        )

        logger.info("GEPA-lite Phase 2: Mutating prompts/system.md...")
        try:
            mutate_result = self.engine._run_llm(
                mutate_prompt, ws_root,
                system_prompt=mutate_system,
                evolver_workspace=evo_ws,
            )
        except Exception as e:
            logger.warning("Phase 2 (mutate) failed: %s", e)
            vc.rollback_to_tag(pre_mutate_tag)
            trajectory.append({"step": "mutate", "mutated": False, "error": str(e)})
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # Surface-area guardrail: revert if anything outside prompts/ changed.
        # Stage unstaged changes first so `git diff` sees them; use HEAD so
        # we catch both modifications and untracked files.
        try:
            vc._git("add", "-A")
        except Exception:
            pass
        changed: set[str] = set()
        for args in (
            ("diff", "--name-only", pre_mutate_tag, "HEAD"),
            ("diff", "--name-only", "--cached", "HEAD"),
        ):
            try:
                out = vc._git(*args)
                changed.update(f for f in out.splitlines() if f.strip())
            except Exception:
                pass
        out_of_scope = sorted(f for f in changed if not f.startswith("prompts/"))

        if out_of_scope:
            logger.warning(
                "GEPA-lite mutation touched out-of-scope files: %s — reverting",
                out_of_scope,
            )
            vc.rollback_to_tag(pre_mutate_tag)
            trajectory.append({
                "step": "mutate", "mutated": False,
                "out_of_scope": out_of_scope, "reverted": True,
            })
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        mutated = vc.commit(
            message=f"evo-{evo_number}-gepa-mutate: prompts/system.md revision",
            tag=f"evo-{evo_number}-mutate",
        )
        trajectory.append({
            "step": "mutate", "mutated": mutated, "out_of_scope": [],
            "conversation": mutate_result.get("conversation", [])
            if isinstance(mutate_result, dict) else [],
        })

        return {
            "evo_number": evo_number, "mutated": mutated, "plan": {},
            "branches": tree.branch_names(), "trajectory": trajectory,
        }
