"""ActionRegistry — maps spec ``kind`` strings to node classes.

Concrete ``Action`` subclasses live in ``nodes/*.py`` and register
themselves on import by calling ``default_registry().register(cls)``.
The registry also holds the control-flow node classes and the
``CallActivity`` node so specs can reference any node kind by string.

Swapping an implementation (e.g. a custom ``op.call_llm`` that uses a
different provider) is a one-line ``registry.register(MyCallLLM)``.
"""

from __future__ import annotations

from typing import Any

from .action import Action
from .activity_node import ActivityNode
from .call_activity import CallActivity
from .control import (
    DecisionNode,
    ExpansionRegion,
    FinalNode,
    ForkNode,
    InitialNode,
    JoinNode,
)


class ActionRegistry:
    """Holds the mapping from ``kind`` / ``action_kind`` to node classes.

    ``lookup(node_spec)`` resolves a ``NodeSpec`` to the class the runtime
    should instantiate.  For ``Action`` nodes, the lookup uses
    ``config["action_kind"]``; for everything else, the ``kind`` string.
    """

    def __init__(self) -> None:
        self._by_kind: dict[str, type[ActivityNode]] = {}
        self._actions: dict[str, type[Action]] = {}
        self._register_control_nodes()

    def _register_control_nodes(self) -> None:
        for cls in (
            InitialNode,
            FinalNode,
            DecisionNode,
            ForkNode,
            JoinNode,
            ExpansionRegion,
            CallActivity,
        ):
            self._by_kind[cls.kind] = cls

    def register(self, cls: type[Action]) -> None:
        """Register a concrete ``Action`` class by its ``action_kind``."""
        if not cls.action_kind:
            raise ValueError(f"Action subclass {cls.__name__} missing action_kind")
        self._actions[cls.action_kind] = cls

    def lookup(self, node_spec: Any) -> type[ActivityNode]:
        """Resolve a ``NodeSpec`` to the node class the runtime will use."""
        if node_spec.kind == "Action":
            ak = node_spec.config.get("action_kind")
            if ak not in self._actions:
                raise KeyError(f"Unknown action_kind: {ak!r}")
            return self._actions[ak]
        if node_spec.kind not in self._by_kind:
            raise KeyError(f"Unknown node kind: {node_spec.kind!r}")
        return self._by_kind[node_spec.kind]

    def list_actions(self) -> list[str]:
        return sorted(self._actions)

    def list_kinds(self) -> list[str]:
        return sorted(self._by_kind)


_DEFAULT: ActionRegistry | None = None


def default_registry() -> ActionRegistry:
    """Lazily constructed process-wide registry with built-ins registered.

    Import of ``.nodes`` triggers its ``register_builtins()`` side effect.
    That module is loaded only inside this function so Layer 3 cannot
    leak into Layer 2 consumers that touch only the registry.
    """
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = ActionRegistry()
        # Lazy import to keep the registry usable before nodes exist.
        try:
            from . import nodes  # noqa: F401  (registration side effect)

            nodes.register_builtins(_DEFAULT)
        except Exception:
            # Phase 1/2: nodes package may not exist yet.  Callers that
            # need built-ins will import them explicitly.
            pass
    return _DEFAULT
