"""Meta-Harness-lite — archive proposer with growing filesystem archive.

Fair-comparison port of Meta-Harness (Lee et al., 2026). Preserves the
paper's distinctive mechanism — a growing ``evolution/candidates/`` archive
the proposer browses via bash — while dropping features that are
incompatible with our trajectory-only temporal-reveal setup:
  - k=1 per cycle (paper default k=2) to equalize per-cycle proposer
    compute with A-Evolve and our method.
  - No score-gated selection or rollback. The observer gate strips scalar
    scores before templates see batch_results, so the paper's
    ``_evaluate_candidate`` pathway is inaccessible. "Last proposed wins"
    matches A-Evolve's and our method's no-regret loop.

Single-phase cycle per evolution:
  Phase A (snapshot): copy prompts/skills/memory/tools/ + selected files
                      into evolution/candidates/cycle_NNN_cand_1/snapshot/;
                      write traces/batch.jsonl from batch_results (already
                      label-scrubbed by the observer).
  Phase B (propose):  one bash-enabled LLM call browses the archive and
                      edits any of prompts/, skills/, memory/, tools/,
                      infra/, harness.py. The applied proposal is the
                      final workspace state after the call returns.

Activated via config: ``orchestrator: meta_harness_lite``
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._evolution_workspace import (
    get_evolver_workspace_path,
    init_evolution_workspace,
)

logger = logging.getLogger(__name__)

_GENERAL_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Mirror of meta_harness/engine.py constants so we don't create a cross-package
# dependency on the standalone engine (which has its own eval loop).
_SNAPSHOT_DIRS = ("prompts", "skills", "memory", "tools", "infra", ".claude")
_SNAPSHOT_FILES = ("harness.py", "CLAUDE.md")


def _load_prompt(prompts_dir: Path | None, name: str, fallback: str = "") -> str:
    """Load a general prompt and merge benchmark-specific context."""
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


def _snapshot_workspace(ws_root: Path, dest: Path) -> dict[str, int]:
    """Copy snapshot dirs and files into dest. Returns bytecount stats."""
    dest.mkdir(parents=True, exist_ok=True)
    stats = {"dirs": 0, "files": 0, "bytes": 0}

    def _ignore(_src, names):
        return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]

    for dirname in _SNAPSHOT_DIRS:
        src = ws_root / dirname
        if src.is_dir():
            dst = dest / dirname
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=_ignore)
            stats["dirs"] += 1
            for p in dst.rglob("*"):
                if p.is_file():
                    stats["files"] += 1
                    try:
                        stats["bytes"] += p.stat().st_size
                    except Exception:
                        pass
    for fname in _SNAPSHOT_FILES:
        src = ws_root / fname
        if src.is_file():
            shutil.copy2(src, dest / fname)
            stats["files"] += 1
            try:
                stats["bytes"] += src.stat().st_size
            except Exception:
                pass
    return stats


def _write_traces(cand_dir: Path, batch_results: list[dict]) -> int:
    """Write batch_results (already reveal-gated) as one JSON per line."""
    traces = cand_dir / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    out = traces / "batch.jsonl"
    lines = []
    for r in batch_results:
        try:
            lines.append(json.dumps(r, default=str))
        except Exception:
            lines.append(json.dumps({"instance_id": r.get("instance_id", "?"),
                                     "serialize_error": True}))
    out.write_text("\n".join(lines))
    return len(lines)


class Template(EvolutionTemplate):
    """Archive snapshot → single-call proposer, k=1 per cycle."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "meta_harness_lite"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        mh_config = cfg.extra.get("meta_harness_lite", {})
        prompts_dir_str = mh_config.get("prompts_dir", "")
        prompts_dir = Path(prompts_dir_str) if prompts_dir_str else None

        ws_root = solver_workspace.root
        evo_ws = get_evolver_workspace_path(ws_root)
        init_evolution_workspace(evo_ws)

        trajectory: list[dict] = []

        # ── Phase A: snapshot pre-proposal state into archive ────
        candidates_dir = ws_root / "evolution" / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        n_archived = len([d for d in candidates_dir.iterdir() if d.is_dir()])

        cand_dir = candidates_dir / f"cycle_{evo_number:03d}_cand_1"
        if cand_dir.exists():
            shutil.rmtree(cand_dir)
        cand_dir.mkdir(parents=True)

        snap_stats = _snapshot_workspace(ws_root, cand_dir / "snapshot")
        n_traces = _write_traces(cand_dir, batch_results)
        (cand_dir / "meta.json").write_text(json.dumps({
            "cycle": evo_number,
            "cand": 1,
            "batch_size": len(batch_results),
            "snapshot": snap_stats,
            "n_prior_archived": n_archived,
        }, indent=2))

        vc.commit(
            message=f"evo-{evo_number}-mh-snapshot: archived cycle {evo_number} "
                    f"({snap_stats['files']} files, {n_traces} traces)",
            tag=f"evo-{evo_number}-mh-pre",
        )
        trajectory.append({
            "step": "snapshot",
            "n_prior_archived": n_archived,
            "files": snap_stats["files"],
            "bytes": snap_stats["bytes"],
            "n_traces": n_traces,
        })

        # ── Phase B: proposer (single LLM call, full workspace bash) ─
        proposer_prompt = _load_prompt(
            prompts_dir, "mh_proposer.md", "Propose one minimal change.",
        ).format(
            evo_number=evo_number,
            num_archived=n_archived + 1,
            batch_size=len(batch_results),
        )
        proposer_system = _load_prompt(
            prompts_dir, "mh_proposer_system.md",
            "You are a harness proposer. Browse evolution/candidates/ and "
            "edit the workspace. Do NOT commit. Do NOT touch evolution/.",
        )

        logger.info(
            "Meta-Harness-lite: proposing cycle %d (archive=%d)",
            evo_number, n_archived + 1,
        )

        try:
            result = self.engine._run_llm(
                proposer_prompt, ws_root,
                system_prompt=proposer_system,
                evolver_workspace=evo_ws,
            )
        except Exception as e:
            logger.warning("Meta-Harness-lite proposer failed: %s", e)
            trajectory.append({
                "step": "propose", "mutated": False, "error": str(e),
            })
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # Revert any changes the proposer accidentally made under evolution/.
        # Use porcelain v2 parsing: `git status -z --porcelain=v1` has entries
        # of form "XY path\0" where XY is exactly 2 status chars + 1 space,
        # but file paths may contain spaces so splitting on whitespace is
        # wrong. Use `git diff --name-only` against HEAD after staging,
        # which handles paths correctly.
        try:
            vc._git("add", "-A", "--", "evolution/")
            evo_changed = vc._git(
                "diff", "--name-only", "--cached", "HEAD", "--", "evolution/",
            )
            evo_dirty = [f for f in evo_changed.splitlines() if f.strip()]
            if evo_dirty:
                logger.warning(
                    "Meta-Harness-lite: proposer touched evolution/: %s — reverting those files",
                    evo_dirty,
                )
                for path in evo_dirty:
                    try:
                        vc._git("checkout", "HEAD", "--", path)
                    except Exception:
                        pass
        except Exception:
            pass

        mutated = vc.commit(
            message=f"evo-{evo_number}-mh-propose: cycle {evo_number} proposal",
            tag=f"evo-{evo_number}-mh",
        )
        trajectory.append({
            "step": "propose",
            "mutated": mutated,
            "n_archived": n_archived + 1,
            "usage": result.get("usage", {}) if isinstance(result, dict) else {},
            "conversation": result.get("conversation", [])
            if isinstance(result, dict) else [],
        })

        return {
            "evo_number": evo_number, "mutated": mutated, "plan": {},
            "branches": tree.branch_names(), "trajectory": trajectory,
        }
