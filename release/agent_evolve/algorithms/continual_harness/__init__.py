"""Continual Harness evolution engine (Karten et al., 2025).

Ports the core harness-evolution logic from the Continual Harness framework:
four independent CRUD passes (prompt, skills, memory, tools) analyzing
batch trajectories and mutating the workspace between cycles.
"""

from .engine import ContinualHarnessEngine

__all__ = ["ContinualHarnessEngine"]
