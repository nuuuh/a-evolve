"""Visual studio for designing evolution systems.

A small web UI — served locally from Python stdlib — that lets a user
compose an ``Activity`` (from ``navigation/activity/``) on a canvas,
validate it live, and export a ready-to-use ``EvolutionTemplate``
Python file that drops into ``navigation/templates/``.

Launch::

    python -m agent_evolve.algorithms.navigation.studio

Or programmatically::

    from agent_evolve.algorithms.navigation.studio import launch
    launch(port=8765)
"""

from __future__ import annotations

from .server import launch

__all__ = ["launch"]
