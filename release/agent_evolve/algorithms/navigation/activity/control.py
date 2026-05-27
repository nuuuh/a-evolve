"""UML control-flow nodes: Initial/Final, Decision, Fork/Join, ExpansionRegion.

Each is a thin class satisfying ``ActivityNode``.  ``ExpansionRegion`` is
the primitive that lets a planner spawn N sub-agents: given a collection
on its ``items`` input and a referenced sub-Activity, the runtime invokes
the sub-Activity once per element (iterative or parallel).
"""

from __future__ import annotations

from typing import Any, ClassVar

from .activity_node import ActivityNode
from .pin import InputPin, OutputPin
from .spec import Activity
from .types import Type


class InitialNode(ActivityNode):
    """UML InitialNode — the entry marker of an Activity."""

    kind: ClassVar[str] = "InitialNode"

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        return []

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        return [OutputPin(name="out", type=Type.VOID)]


class FinalNode(ActivityNode):
    """UML ActivityFinalNode — the exit marker of an Activity."""

    kind: ClassVar[str] = "FinalNode"

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        return [InputPin(name="in", type=Type.VOID, required=False)]

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        return []


class DecisionNode(ActivityNode):
    """UML DecisionNode + MergeNode — routes input by a Boolean guard.

    Single input ``in`` of arbitrary type (the datum) plus ``guard`` of
    type Boolean; two outputs ``true`` and ``false`` of the same type
    as ``in``.  The runtime emits the datum on exactly one of the
    outputs per evaluation.
    """

    kind: ClassVar[str] = "DecisionNode"

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        return [
            InputPin(name="guard", type=Type.BOOLEAN),
            InputPin(name="in", type=value_type),
        ]

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        return [
            OutputPin(name="true", type=value_type),
            OutputPin(name="false", type=value_type),
        ]


class ForkNode(ActivityNode):
    """UML ForkNode — duplicates its single input onto N typed outputs."""

    kind: ClassVar[str] = "ForkNode"

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        return [InputPin(name="in", type=value_type)]

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        n = int((config or {}).get("outputs", 2))
        return [OutputPin(name=f"out{i}", type=value_type) for i in range(n)]


class JoinNode(ActivityNode):
    """UML JoinNode — synchronises N inputs into one output."""

    kind: ClassVar[str] = "JoinNode"

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        n = int((config or {}).get("inputs", 2))
        return [InputPin(name=f"in{i}", type=value_type) for i in range(n)]

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        value_type = Type((config or {}).get("value_type", Type.VOID.value))
        return [OutputPin(name="out", type=value_type)]


class ExpansionRegion(ActivityNode):
    """UML ExpansionRegion — "for each" over a collection.

    Config:
        activity: sub-Activity name to invoke per element.
        mode: ``"iterative"`` (default, sequential) or ``"parallel"``.
        item_param: parameter name on the sub-Activity that receives the
            current element (defaults to ``"item"``).
        result_param: optional; if set, the sub-Activity's output with
            that name is collected into a list on the region's
            ``results`` output pin.

    Pins are derived from the referenced sub-Activity's parameters plus
    the ``items`` (input list) and ``results`` (output list) pins.
    """

    kind: ClassVar[str] = "ExpansionRegion"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.activity_name: str = self.config.get("activity", "")
        self.mode: str = self.config.get("mode", "iterative")
        self.item_param: str = self.config.get("item_param", "item")
        self.result_param: str = self.config.get("result_param", "")

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        # Dynamic: resolved by validator from sub-Activity.
        return []

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        return []

    @staticmethod
    def pins_from_sub_activity(
        sub: Activity,
        config: dict[str, Any],
    ) -> tuple[list[InputPin], list[OutputPin]]:
        """Derive region pins from the referenced sub-Activity.

        Produces:
          inputs: ``items`` (a list of ``item_param``'s type) plus one
                  input pin per ``in`` parameter on the sub-Activity
                  *except* the item parameter.
          outputs: optional ``results`` (a list of ``result_param``'s
                   type) plus one output pin per ``out`` parameter
                   *except* the result parameter.
        """
        item_param = config.get("item_param", "item")
        result_param = config.get("result_param", "")

        item_type: Type | None = None
        inputs: list[InputPin] = []
        for p in sub.parameters:
            if p.direction != "in":
                continue
            if p.id == item_param:
                item_type = p.type
                continue
            inputs.append(InputPin(name=p.id, type=p.type))

        # Fold the list-of-items pin.  Default to STRING_LIST if no
        # typed list version of the item type exists; specs usually
        # pass BranchSpecList / StringList directly.
        if item_type is not None:
            list_type = _list_type_for(item_type)
            inputs.insert(0, InputPin(name="items", type=list_type))

        outputs: list[OutputPin] = []
        result_type: Type | None = None
        for p in sub.parameters:
            if p.direction != "out":
                continue
            if p.id == result_param:
                result_type = p.type
                continue
            outputs.append(OutputPin(name=p.id, type=p.type))
        if result_type is not None:
            list_type = _list_type_for(result_type)
            outputs.insert(0, OutputPin(name="results", type=list_type))

        return inputs, outputs


def _list_type_for(element: Type) -> Type:
    """Map an element type to its natural list Type (or STRING_LIST)."""
    if element is Type.BRANCH_SPEC:
        return Type.BRANCH_SPEC_LIST
    if element is Type.STRING:
        return Type.STRING_LIST
    # Fallback: a heterogeneous list.  Runtime treats it as list[Any].
    return Type.STRING_LIST
