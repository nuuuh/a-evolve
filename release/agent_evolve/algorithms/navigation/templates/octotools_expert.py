"""OctoTools-expert — static hand-designed reference baseline.

Faithful adaptation of OctoTools (Lu et al., ACL 2026 oral), a training-free
generalist agentic framework with a Planner + Executor + Tool-Cards
architecture. This implementation preserves the paper's three-phase workflow
(Plan → Execute → Verify) and tool-card pattern, expressed as a single
multi-turn solver call whose system prompt explicitly instructs each phase.
The Planner and Executor are merged into one call rather than run as two
separate LLM invocations because both operate on the same base model in the
original paper and our solver runtime is single-call multi-turn.

Not self-evolving: at cycle 0, this template installs the OctoTools prompts
and tool-card registry into the solver workspace. For all subsequent cycles
it returns ``mutated=False`` without any LLM activity — the static-harness
reference condition.

Two variants via config flag ``octotools_expert.variant``:
  - ``reasoning`` (default): no web search. Used for polybench and ctf_dojo.
  - ``search``: search tool-card is included. Used for futurex.

Activated via config: ``orchestrator: octotools_expert``
"""

from __future__ import annotations

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

    Same pattern as structured_evolution._load_prompt and gepa_lite._load_prompt:
    the general prompt under templates/prompts/<name> contains a
    ``{benchmark_context}`` placeholder which is replaced with content from
    <prompts_dir>/<name> if it exists, otherwise with empty string.
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


def _build_registry_yaml(variant: str) -> str:
    """Emit tools/registry.yaml content referencing OctoTools tool-cards.

    The existing solver reads registry.yaml for a list of {name, description}
    dicts. We do not add new executable .py files — ``workspace_bash`` is
    already the solver's native tool; the tool-cards here are descriptive
    metadata that tells the LLM *when* to use each capability, matching the
    OctoTools paper's Tool-Card concept.
    """
    cards: list[tuple[str, str]] = [
        ("workspace_bash", _load_prompt(None, "octo_tool_card_bash.md").strip()),
        ("inline_python",  _load_prompt(None, "octo_tool_card_python.md").strip()),
    ]
    if variant == "search":
        cards.append(("search", _load_prompt(None, "octo_tool_card_search.md").strip()))

    lines = ["# OctoTools tool-card registry (auto-installed at cycle 0)", "tools:"]
    for name, desc in cards:
        one_line = desc.replace("\n", " ").replace("  ", " ").strip()
        # Keep YAML valid: escape double-quotes in description.
        one_line = one_line.replace('"', "'")
        lines.append(f"  - name: {name}")
        lines.append(f'    description: "{one_line}"')
    return "\n".join(lines) + "\n"


class Template(EvolutionTemplate):
    """Install OctoTools harness at cycle 0; freeze thereafter."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "octotools_expert"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        oc_cfg = cfg.extra.get("octotools_expert", {})
        variant = oc_cfg.get("variant", "reasoning")
        prompts_dir_str = oc_cfg.get("prompts_dir", "")
        prompts_dir = Path(prompts_dir_str) if prompts_dir_str else None

        ws_root = solver_workspace.root
        evo_ws = get_evolver_workspace_path(ws_root)
        init_evolution_workspace(evo_ws)

        trajectory: list[dict] = []

        # Install the OctoTools harness on first call, regardless of
        # whether the framework numbers cycles from 0 or 1. We detect
        # "first call" by the absence of our own install tag. This also
        # makes resume safe: a re-run on an existing workspace sees the
        # tag and skips re-installation.
        already_installed = self._has_install_tag(vc)
        if not already_installed:
            return self._install(
                vc, ws_root, variant, prompts_dir, trajectory, tree, evo_number,
            )

        # Subsequent cycles: static harness — no evolution, no LLM calls.
        logger.info(
            "OctoTools-expert: cycle %d — frozen harness (variant=%s)",
            evo_number, variant,
        )
        trajectory.append({"step": "frozen_harness", "variant": variant})
        return {
            "evo_number": evo_number,
            "mutated": False,
            "plan": {"variant": variant, "frozen": True},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    @staticmethod
    def _has_install_tag(vc) -> bool:
        """Return True if the OctoTools harness has already been installed."""
        try:
            tags = vc._git("tag", "-l", "evo-*-octotools")
            return bool(tags.strip())
        except Exception:
            return False

    def _install(
        self, vc, ws_root: Path, variant: str,
        prompts_dir: Path | None, trajectory: list[dict], tree,
        evo_number: int,
    ) -> dict[str, Any]:
        """Install the OctoTools Planner+Executor prompt + tool-card registry."""
        if variant == "search":
            prompt_name = "octo_system_search.md"
        else:
            prompt_name = "octo_system_reasoning.md"

        system_md = _load_prompt(
            prompts_dir, prompt_name,
            fallback="You are a task-solving agent. Plan, execute, then verify.",
        )
        if not system_md.strip():
            logger.warning(
                "OctoTools-expert: loaded system prompt is empty (variant=%s) — "
                "check templates/prompts/%s",
                variant, prompt_name,
            )

        # Install prompts/system.md.
        prompts_out = ws_root / "prompts"
        prompts_out.mkdir(parents=True, exist_ok=True)
        (prompts_out / "system.md").write_text(system_md)

        # Install tools/registry.yaml with OctoTools tool-cards.
        registry_yaml = _build_registry_yaml(variant)
        tools_out = ws_root / "tools"
        tools_out.mkdir(parents=True, exist_ok=True)
        (tools_out / "registry.yaml").write_text(registry_yaml)

        mutated = vc.commit(
            message=(
                f"evo-{evo_number}-octotools: install {variant} "
                f"Planner+Executor+ToolCards harness"
            ),
            tag=f"evo-{evo_number}-octotools",
        )

        logger.info(
            "OctoTools-expert installed at cycle %d: variant=%s, prompt=%d chars, registry=%d chars, mutated=%s",
            evo_number, variant, len(system_md), len(registry_yaml), mutated,
        )
        trajectory.append({
            "step": "install",
            "variant": variant,
            "evo_number": evo_number,
            "prompt_chars": len(system_md),
            "registry_chars": len(registry_yaml),
            "mutated": mutated,
        })
        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {"variant": variant, "installed": True},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
