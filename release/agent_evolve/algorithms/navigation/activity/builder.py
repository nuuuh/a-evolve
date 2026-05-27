"""Fluent Python builder for an ``Activity``.

Provides a chainable API so designers don't have to hand-write JSON:

    activity = (
        ActivityBuilder("my_flow")
        .parameter("ws",   Type.WORKSPACE)
        .parameter("cfg",  Type.CONFIG)
        .node("snap", "Action", action_kind="op.snapshot_workspace")
        .object_flow("ws", "snap.workspace")
        .build()
    )

``build()`` runs the validator so typing errors surface at construction
time.
"""

from __future__ import annotations

from typing import Any

from .registry import ActionRegistry, default_registry
from .spec import Activity, FlowSpec, NodeSpec, ParameterSpec
from .types import Type
from .validator import validate


class ActivityBuilder:
    """Fluent builder for an Activity."""

    def __init__(self, name: str, description: str = ""):
        self._activity = Activity(name=name, description=description)

    def parameter(
        self, id: str, type: Type, direction: str = "in"
    ) -> ActivityBuilder:
        self._activity.parameters.append(
            ParameterSpec(id=id, type=type, direction=direction)  # type: ignore[arg-type]
        )
        return self

    def node(self, id: str, kind: str, **config: Any) -> ActivityBuilder:
        self._activity.nodes.append(NodeSpec(id=id, kind=kind, config=config))
        return self

    def action(self, id: str, action_kind: str, **config: Any) -> ActivityBuilder:
        """Convenience: shorthand for .node(id, 'Action', action_kind=..., **config)."""
        return self.node(id, "Action", action_kind=action_kind, **config)

    def object_flow(self, source: str, target: str) -> ActivityBuilder:
        self._activity.flows.append(
            FlowSpec(kind="ObjectFlow", source=source, target=target)
        )
        return self

    def control_flow(self, source: str, target: str) -> ActivityBuilder:
        self._activity.flows.append(
            FlowSpec(kind="ControlFlow", source=source, target=target)
        )
        return self

    def sub_activity(self, name: str, activity: Activity) -> ActivityBuilder:
        self._activity.sub_activities[name] = activity
        return self

    def build(self, registry: ActionRegistry | None = None) -> Activity:
        """Validate and return the Activity."""
        registry = registry or default_registry()
        validate(self._activity, registry)
        return self._activity

    def build_unchecked(self) -> Activity:
        """Return without validation — for tests that assert bad specs."""
        return self._activity
