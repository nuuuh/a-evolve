"""UML CallBehaviorAction — a node that invokes a nested Activity.

At validation and runtime the node's pins are resolved from the called
Activity's ``in``/``out`` parameters, so the containing Activity sees the
sub-Activity as a typed box with matching pins.
"""

from __future__ import annotations

from typing import Any, ClassVar

from .activity_node import ActivityNode
from .pin import InputPin, OutputPin
from .spec import Activity


class CallActivity(ActivityNode):
    """Invokes a sub-Activity by name.

    ``config["activity"]`` is the sub-Activity name.  Pins are resolved
    from the referenced sub-Activity's parameters — so validation errors
    surface if the referenced Activity is missing or its parameter types
    don't match the wired values.
    """

    kind: ClassVar[str] = "CallActivity"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.activity_name: str = self.config.get("activity", "")

    @classmethod
    def input_pins(cls, config: dict[str, Any] | None = None) -> list[InputPin]:
        # Pins are resolved by the validator from the containing
        # Activity's ``sub_activities`` dict; here we return an empty
        # list to signal "dynamic — ask the enclosing Activity".
        return []

    @classmethod
    def output_pins(cls, config: dict[str, Any] | None = None) -> list[OutputPin]:
        return []

    @staticmethod
    def pins_from_sub_activity(
        sub: Activity,
    ) -> tuple[list[InputPin], list[OutputPin]]:
        """Derive typed pins from a referenced sub-Activity's parameters."""
        inputs: list[InputPin] = []
        outputs: list[OutputPin] = []
        for p in sub.parameters:
            if p.direction == "in":
                inputs.append(InputPin(name=p.id, type=p.type))
            else:
                outputs.append(OutputPin(name=p.id, type=p.type))
        return inputs, outputs
