"""Built-in node catalog.

Each module in this package registers one or more concrete ``Action``
subclasses with the registry.  Agent sub-Activities live under
``nodes/agents/`` and are exposed via ``build_*_activity()`` factories;
they are not auto-registered (they are Activities, not Actions).

Import side effects: importing this package triggers
``register_builtins()`` on the default registry.
"""

from __future__ import annotations

from ..registry import ActionRegistry
from .agents import (
    build_analyst_activity,
    build_critic_activity,
    build_evolver_activity,
    build_planner_activity,
)

__all__ = [
    "register_builtins",
    "build_analyst_activity",
    "build_critic_activity",
    "build_evolver_activity",
    "build_planner_activity",
]


def register_builtins(registry: ActionRegistry) -> None:
    """Register every built-in Action with the given registry.

    Called once by ``default_registry()`` on first use.
    """
    from . import git as _git
    from . import llm as _llm
    from . import navigation as _navigation
    from . import prompt as _prompt
    from . import workspace as _workspace

    for module in (_workspace, _prompt, _llm, _git, _navigation):
        for cls in module.BUILTINS:
            registry.register(cls)
