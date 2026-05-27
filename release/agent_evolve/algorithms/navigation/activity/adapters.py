"""Bridge between an ``Activity`` and the existing evolution engine.

``ActivityTemplate`` wraps an Activity as an ``EvolutionTemplate`` so it
can be passed to ``NavigationEngine(config, template=...)``.  The
navigation engine treats every evolution mode as "an Activity run by a
template"; there is no separate orchestrator abstraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..templates.base import EvolutionTemplate
from .registry import ActionRegistry, default_registry
from .runtime import ActivityRuntime, RunContext
from .spec import Activity

if TYPE_CHECKING:
    from ....contract.workspace import AgentWorkspace
    from ....engine.versioning import VersionControl
    from ....types import StrategyTree
    from ..engine import NavigationEngine


class ActivityTemplate(EvolutionTemplate):
    """Runs an ``Activity`` as an ``EvolutionTemplate``.

    Bindings exposed to the Activity's parameters:
        workspace  -> solver_workspace
        git        -> (vc, tree) tuple
        batch      -> batch_results
        cfg        -> engine.config
        evo_number -> evo_number
        routing    -> str(routing_log_path) or ""

    ``ctx.extra["engine"]`` carries the engine so ``op.call_llm`` and
    ``op.call_llm_simple`` can reach its sandbox and LLM.
    """

    def __init__(
        self,
        activity: Activity,
        engine: NavigationEngine,
        *,
        registry: ActionRegistry | None = None,
        binding_names: dict[str, str] | None = None,
    ):
        self.activity = activity
        self.engine = engine
        self.registry = registry or default_registry()
        self.runtime = ActivityRuntime(self.registry)
        # Parameter-id overrides, if the spec uses different names.
        self._binding_names = binding_names or {}

    @property
    def name(self) -> str:
        return f"activity:{self.activity.name}"

    def execute(
        self,
        vc: VersionControl,
        solver_workspace: AgentWorkspace,
        batch_results: list[dict[str, Any]],
        tree: StrategyTree,
        evo_number: int,
        routing_log_path: Path | None,
    ) -> dict[str, Any]:
        workspace_id = self._binding_names.get("workspace", "workspace")
        git_id = self._binding_names.get("git", "git")
        batch_id = self._binding_names.get("batch", "batch")
        cfg_id = self._binding_names.get("cfg", "cfg")
        evo_id = self._binding_names.get("evo_number", "evo_number")
        routing_id = self._binding_names.get("routing", "routing_log")

        bindings: dict[str, Any] = {
            workspace_id: solver_workspace,
            git_id: (vc, tree),
            batch_id: batch_results,
            cfg_id: self.engine.config,
            evo_id: evo_number,
            routing_id: str(routing_log_path) if routing_log_path else "",
        }

        ctx = RunContext(registry=self.registry, runtime=self.runtime)
        ctx.extra["engine"] = self.engine

        # Keep only bindings the Activity declares, so validator-
        # accepted specs with fewer parameters don't explode.
        declared = {p.id for p in self.activity.parameters}
        filtered = {k: v for k, v in bindings.items() if k in declared}

        outputs = self.runtime.run(self.activity, filtered, ctx=ctx)

        return {
            "evo_number": evo_number,
            "mutated": _pick(outputs, "mutated", default=False),
            "plan": _pick(outputs, "plan", default={}),
            "branches": tree.branch_names(),
            "trajectory": ctx.trace,
        }


def _pick(outputs: dict[str, Any], name: str, *, default: Any) -> Any:
    """Find ``name`` among computed outputs.

    First checks for a bare key (an Activity out-parameter); then
    searches any key ending in ``.name``.
    """
    if name in outputs:
        return outputs[name]
    suffix = "." + name
    for k, v in outputs.items():
        if k.endswith(suffix):
            return v
    return default
