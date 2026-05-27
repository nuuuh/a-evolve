"""ActivityNode ABC + Behavior ABC.

UML's ``ActivityNode`` is the supertype of every node kind that can
appear inside an Activity (Action, CallBehaviorAction, DecisionNode,
ForkNode, JoinNode, ExpansionRegion, InitialNode, FinalNode).

Every concrete node subclass declares its typed input/output pins as
class methods so the validator can check wire types statically, before
any Activity runs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .pin import InputPin, OutputPin


class Behavior(ABC):
    """UML Behavior — an invokable body.

    Has two concrete subtypes in this framework: a concrete ``Action``
    (the body is Python code) and an ``Activity`` (the body is a nested
    graph of ActivityNodes).  Kept minimal so subclasses stay tiny.
    """


class ActivityNode(ABC):
    """UML ActivityNode — base for every node kind inside an Activity."""

    # Each subclass sets this class var to the spec ``kind`` string.
    kind: ClassVar[str] = ""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config: dict[str, Any] = dict(config or {})

    @classmethod
    @abstractmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        """Typed input pins.  ``config`` allows pins to be config-dependent
        (e.g. ``ExpansionRegion`` pins mirror the called sub-Activity)."""

    @classmethod
    @abstractmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        """Typed output pins.  ``config`` mirrors ``input_pins``."""
