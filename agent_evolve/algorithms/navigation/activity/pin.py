"""Typed pins on an ``ActivityNode``.

UML distinguishes InputPin and OutputPin as separate classes — both are
value-carrying ports on an ActivityNode.  The ``type`` field is checked
by the validator against every incoming/outgoing ObjectFlow.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import Type


@dataclass(frozen=True)
class InputPin:
    """UML InputPin — a typed input on an ActivityNode."""

    name: str
    type: Type
    required: bool = True


@dataclass(frozen=True)
class OutputPin:
    """UML OutputPin — a typed output on an ActivityNode."""

    name: str
    type: Type
