"""Built-in evolution algorithm implementations.

Canonical engines in the V2 fork:
  - ``aevolve``         -- V2's LLM-driven workspace mutation (default).
  - ``navigation``      -- branch routing + holistic analysis (peer).
  - ``skillforge``      -- alias → re-exports aevolve + navigation for
                          callers written against upstream.

Optional upstream engines preserved for cross-experiment use:
  - ``mas_adaptive_skill`` -- 4-agent orchestrator/analyst/author/critic.
  - ``meta_harness``    -- Claude Code CLI as proposer.
  - ``gepa``            -- Genetic Evolution via Prompting Agents.

The upstream ``adaptive_skill``, ``adaptive_evolve``, and ``guided_synth``
packages have been removed because they are being replaced by the
UnifiedEngine refactor on upstream ``main``.  The V2 engine will migrate
to the UnifiedEngine atom model in Phase 8 of the rebase plan.
"""

from .aevolve import AEvolveEngine
from .navigation import NavigationEngine

try:
    from .mas_adaptive_skill import MasAdaptiveSkillEngine
except (ImportError, ModuleNotFoundError):
    # MAS engine depends on adaptive_skill (removed in this fork).
    # Silently unavailable — callers check for None before use.
    MasAdaptiveSkillEngine = None

try:
    from .meta_harness import MetaHarnessEngine
except ImportError:
    MetaHarnessEngine = None

__all__ = [
    "AEvolveEngine",
    "NavigationEngine",
    "MasAdaptiveSkillEngine",
    "MetaHarnessEngine",
]
