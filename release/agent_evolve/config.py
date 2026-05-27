"""Evolution configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EvolveConfig:
    """Configuration for an evolution run.

    The ``extra`` dict supports the following MCP-related keys:

    - ``mcp_env_file`` (str): Path to a ``.env`` file containing API keys.
      Falls back to the ``MCP_ENV_FILE`` environment variable. Default: ``".env"``.
    - ``mcp_aws_secret_name`` (str): AWS Secrets Manager secret name for API keys.
    - ``mcp_aws_region`` (str): AWS region for Secrets Manager lookups.
    - ``mcp_server_key_map`` (str): Path to a custom YAML server-to-key mapping file.
    """

    batch_size: int = 10
    max_cycles: int = 20
    holdout_ratio: float = 0.0  # V2 benchmarks pre-split; upstream default was 0.2

    # Gating: which layers the evolver is allowed to mutate
    evolve_prompts: bool = True
    evolve_skills: bool = True
    evolve_memory: bool = True
    evolve_tools: bool = False
    evolve_infra: bool = True  # V2: infra/ layer (framework-run pipelines with network access)

    # When True, the evolver only sees agent trajectories (tool calls and
    # outputs) — no pass/fail, score, or test output.  This forces the
    # meta-learner to infer improvement opportunities from behavior alone.
    trajectory_only: bool = False

    # When True, feedback is revealed per-task iff the task's
    # resolution date is on or before the current batch timestamp
    # (computed as ``max(task.creation_date)`` across the batch).
    # Orthogonal to and overrides ``trajectory_only`` per-task — the
    # realistic "drip of truth" mode for benchmarks with temporal
    # resolution (FutureX, PolyBench).  CTF tasks have no resolution
    # date so their labels remain hidden.
    temporal_reveal: bool = False

    # Evolver LLM
    evolver_model: str = "<evolver-model-id>"
    evolver_max_tokens: int = 16384
    evolver_temperature: float = 0.0  # V2: evolver LLM temperature
    evolver_include_patches: bool = False  # V2: no-op in index mode; legacy inline only

    # Trajectory feed mode.
    #  - "index" (default, privacy-safe): the evolver prompt carries only a
    #    compact index of recent trajectories (task_id, batch, cycle_age,
    #    turns, task_input_preview, trajectory_file, patch_file). Full
    #    trajectories are pulled on demand via workspace_bash against the
    #    read-only /trajectories mount. Evaluation signals (success,
    #    score, feedback, judge claims) are NEVER exposed.
    #  - "inline" (legacy): inlines full conversation arrays plus
    #    ground-truth fields directly in the prompt. Kept only for parity
    #    testing against old baselines; unsafe for real evolution runs.
    evolver_trajectory_mode: str = "index"

    # Parallelism (V2)
    solve_workers: int = 1

    # Convergence
    egl_threshold: float = 0.05
    egl_window: int = 3

    # Navigation (V2 --navigation flag; disabled by default = current AdaptiveAutoHarness)
    navigation_enabled: bool = False
    branch_confidence_threshold: float = 0.7  # evolver confidence to create branch
                                              # -1 = never branch (linear fallback)
    promotion_threshold: float = 0.15  # cross-region improvement to merge branch
    staleness_window: int = 5  # prune branches unused for N cycles

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvolveConfig:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        raw = _expand_env(raw)
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        known = {k: v for k, v in raw.items() if k in known_fields}
        extra = {k: v for k, v in raw.items() if k not in known_fields}
        return cls(**known, extra=extra)


def _expand_env(value: Any) -> Any:
    """Recursively expand ``${VAR}``/``$VAR`` references and the
    placeholders ``<solver-model-id>`` / ``<evolver-model-id>`` /
    ``<model-id>`` in string-valued YAML entries.

    The placeholders are resolved from ``SOLVER_MODEL`` /
    ``EVOLVER_MODEL`` / ``MODEL`` environment variables respectively.
    Unresolved placeholders are returned unchanged so the caller sees
    a clear error if the model is never supplied.
    """
    import os as _os

    placeholder_map = {
        "<solver-model-id>": _os.environ.get("SOLVER_MODEL", "<solver-model-id>"),
        "<evolver-model-id>": _os.environ.get("EVOLVER_MODEL", "<evolver-model-id>"),
        "<model-id>": _os.environ.get("MODEL", "<model-id>"),
    }

    def _expand_str(s: str) -> str:
        s = _os.path.expandvars(s)
        for key, repl in placeholder_map.items():
            if key in s:
                s = s.replace(key, repl)
        return s

    if isinstance(value, str):
        return _expand_str(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value
