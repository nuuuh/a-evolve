"""SkillForge -- alias for V2's AEvolveEngine + NavigationEngine.

Upstream's canonical name for the core LLM-driven workspace mutation
engine was ``skillforge``.  In the V2 fork the canonical module is
``agent_evolve.algorithms.aevolve`` with navigation promoted to a peer
package.  This alias re-exports everything under the upstream name so
callers written against upstream (``from agent_evolve.algorithms.skillforge
import AEvolveEngine``) continue to work unchanged.

This package will be the landing zone for the UnifiedEngine migration
in Phase 8; the upstream ``skillforge`` module files (engine.py,
prompts.py, tools.py, gating.py, egl.py) are scheduled for removal in
Phase 5 since they will be replaced by the UnifiedEngine + atoms.
"""

from ..aevolve import (  # noqa: F401
    BASH_TOOL_SPEC,
    AEvolveEngine,
    DEFAULT_EVOLVER_SYSTEM_PROMPT,
    make_workspace_bash,
)
from ..navigation.engine import NavigationEngine  # noqa: F401

__all__ = [
    "AEvolveEngine",
    "NavigationEngine",
    "DEFAULT_EVOLVER_SYSTEM_PROMPT",
    "BASH_TOOL_SPEC",
    "make_workspace_bash",
]
