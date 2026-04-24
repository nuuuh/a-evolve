"""Pre-built agent sub-Activities.

Each module exposes a factory ``build_*_activity()`` that returns an
``Activity`` suitable for reference from a ``CallActivity`` or
``ExpansionRegion`` node.

Agents are not ``Action`` subclasses — they are *small activities* that
compose multiple ``Action``s into a reusable pattern.  That way users
can inspect them, modify them, or build their own with the same
building blocks.
"""

from __future__ import annotations

from .analyst import build_analyst_activity
from .critic import build_critic_activity
from .evolver import build_evolver_activity
from .planner import build_planner_activity

__all__ = [
    "build_analyst_activity",
    "build_critic_activity",
    "build_evolver_activity",
    "build_planner_activity",
]
