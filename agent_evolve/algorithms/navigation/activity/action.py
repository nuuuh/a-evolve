"""UML OpaqueAction — a node whose body is a single Python function.

Concrete ``Action`` subclasses live in ``nodes/*.py`` and register under
a short ``action_kind`` string (e.g. ``"op.snapshot_workspace"``).  The
registry maps those strings to classes so specs can refer to actions by
name without importing them.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, ClassVar

from .activity_node import ActivityNode, Behavior

# Note: ``ctx`` is typed as ``Any`` here to keep Action (Layer 2) free of
# any dependency on ``RunContext`` (Layer 4).  Concrete Action subclasses
# may narrow the type in their own annotations if they want editor
# support; the framework only relies on duck-typed attributes (``logger``,
# ``trace``, ``extra``) that ``RunContext`` happens to provide.


class Action(ActivityNode, Behavior):
    """UML OpaqueAction — does one typed thing and returns.

    Subclasses must:
      - set ``action_kind`` (stable identifier for specs and registries)
      - implement ``input_pins()`` and ``output_pins()``
      - implement ``execute(inputs, ctx) -> dict[str, Any]``
    """

    kind: ClassVar[str] = "Action"
    action_kind: ClassVar[str] = ""

    @abstractmethod
    def execute(self, inputs: dict[str, Any], ctx: Any) -> dict[str, Any]:
        """Run the action body.

        Args:
            inputs: ``{pin_name: value}`` for every wired input pin.
            ctx: shared run context for logging and sub-Activity lookup.

        Returns:
            ``{pin_name: value}`` for every output pin this action produces.
        """
