"""Pre-flight validator for an ``Activity``.

Catches every class of design error the runtime would otherwise hit
mid-run:

  1. Every wire's source pin type == target pin type.
  2. No cycles in the ObjectFlow graph of a single Activity.
  3. Every required input pin of every node is wired.
  4. Every sub-Activity name referenced by ``CallActivity`` /
     ``ExpansionRegion`` exists in the containing Activity's
     ``sub_activities``.
  5. ControlFlow endpoints are ``Void`` pins (the implicit Void pins of
     ``InitialNode`` / ``FinalNode``).

Raises ``ActivityValidationError`` with node/flow locations.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .activity_node import ActivityNode
from .call_activity import CallActivity
from .control import ExpansionRegion, FinalNode, InitialNode
from .flow import Endpoint
from .pin import InputPin, OutputPin
from .registry import ActionRegistry
from .spec import Activity, FlowSpec, NodeSpec
from .types import Type


class ActivityValidationError(Exception):
    """Raised when an ``Activity`` fails structural or type validation."""


# ── Pin resolution ───────────────────────────────────────────────────


def _resolve_pins(
    node_spec: NodeSpec,
    activity: Activity,
    registry: ActionRegistry,
) -> tuple[list[InputPin], list[OutputPin]]:
    """Return the pins a node actually has in this Activity.

    For static nodes (most), pins come from the class.  For
    ``CallActivity`` and ``ExpansionRegion`` pins are derived from the
    referenced sub-Activity.
    """
    cls = registry.lookup(node_spec)

    if cls is CallActivity:
        sub_name = node_spec.config.get("activity", "")
        if sub_name not in activity.sub_activities:
            raise ActivityValidationError(
                f"CallActivity {node_spec.id!r} references unknown "
                f"sub-Activity {sub_name!r}"
            )
        return CallActivity.pins_from_sub_activity(activity.sub_activities[sub_name])

    if cls is ExpansionRegion:
        sub_name = node_spec.config.get("activity", "")
        if sub_name not in activity.sub_activities:
            raise ActivityValidationError(
                f"ExpansionRegion {node_spec.id!r} references unknown "
                f"sub-Activity {sub_name!r}"
            )
        return ExpansionRegion.pins_from_sub_activity(
            activity.sub_activities[sub_name], node_spec.config
        )

    return cls.input_pins(node_spec.config), cls.output_pins(node_spec.config)


# ── Core validation ──────────────────────────────────────────────────


def validate(activity: Activity, registry: ActionRegistry) -> None:
    """Validate one Activity + every nested sub-Activity.

    Walks recursively so a failure in a deeply nested sub-Activity is
    caught at the top-level call.
    """
    _validate_one(activity, registry)
    for sub in activity.sub_activities.values():
        validate(sub, registry)


def _validate_one(activity: Activity, registry: ActionRegistry) -> None:
    node_ids = {n.id for n in activity.nodes}
    param_ids = {p.id for p in activity.parameters}

    # Uniqueness
    _check_unique(activity)

    # Resolve all node pins once
    node_pins: dict[str, tuple[list[InputPin], list[OutputPin]]] = {}
    for n in activity.nodes:
        node_pins[n.id] = _resolve_pins(n, activity, registry)

    # Build wire indices
    by_target: dict[str, list[FlowSpec]] = defaultdict(list)
    for f in activity.flows:
        tgt = Endpoint.parse(f.target)
        by_target[str(tgt)].append(f)

    # 1 + 5: typecheck every flow
    for f in activity.flows:
        src = Endpoint.parse(f.source)
        tgt = Endpoint.parse(f.target)

        if f.kind == "ControlFlow":
            # ControlFlow represents pure ordering — in UML it may
            # connect any two ActivityNodes.  When an endpoint names a
            # pin it must be Void-typed; bare endpoints (node id only)
            # are always legal.
            for ep, role in [(src, "source"), (tgt, "target")]:
                if ep.pin is None:
                    # Bare node trigger — ok.
                    continue
                etype = _endpoint_type(
                    ep, activity, node_pins, is_output=(role == "source"),
                )
                if etype is not Type.VOID:
                    raise ActivityValidationError(
                        f"ControlFlow {f.source} -> {f.target}: "
                        f"{role} pin has non-Void type {etype.value!r}"
                    )
        else:
            src_type = _endpoint_type(src, activity, node_pins, is_output=True)
            tgt_type = _endpoint_type(tgt, activity, node_pins, is_output=False)
            if src_type is not tgt_type:
                raise ActivityValidationError(
                    f"ObjectFlow {f.source} -> {f.target}: "
                    f"type mismatch {src_type.value!r} -> {tgt_type.value!r}"
                )

    # 3: every required input pin is wired
    for n in activity.nodes:
        inputs, _ = node_pins[n.id]
        for pin in inputs:
            if not pin.required:
                continue
            key = f"{n.id}.{pin.name}"
            if key not in by_target:
                raise ActivityValidationError(
                    f"Node {n.id!r} required input pin {pin.name!r} "
                    f"({pin.type.value}) is not wired"
                )

    # Flow endpoints must refer to known nodes/parameters
    for f in activity.flows:
        for raw in (f.source, f.target):
            ep = Endpoint.parse(raw)
            if ep.pin is None:
                # bare endpoint: either an Activity parameter or a
                # node id (for Initial/Final which accept bare refs).
                if ep.node not in node_ids and ep.node not in param_ids:
                    raise ActivityValidationError(
                        f"Flow endpoint {raw!r} does not reference a known "
                        f"node or parameter in Activity {activity.name!r}"
                    )
            else:
                if ep.node not in node_ids:
                    raise ActivityValidationError(
                        f"Flow endpoint {raw!r} references unknown node "
                        f"{ep.node!r} in Activity {activity.name!r}"
                    )

    # 2: no cycles in the ObjectFlow graph
    _check_acyclic(activity)


def _check_unique(activity: Activity) -> None:
    seen_nodes: set[str] = set()
    for n in activity.nodes:
        if n.id in seen_nodes:
            raise ActivityValidationError(
                f"Activity {activity.name!r} has duplicate node id {n.id!r}"
            )
        seen_nodes.add(n.id)
    seen_params: set[str] = set()
    for p in activity.parameters:
        if p.id in seen_params:
            raise ActivityValidationError(
                f"Activity {activity.name!r} has duplicate parameter id {p.id!r}"
            )
        seen_params.add(p.id)
    collision = seen_nodes & seen_params
    if collision:
        raise ActivityValidationError(
            f"Activity {activity.name!r} has overlapping node/parameter ids: "
            f"{sorted(collision)!r}"
        )


def _check_acyclic(activity: Activity) -> None:
    adj: dict[str, list[str]] = defaultdict(list)
    nodes = {n.id for n in activity.nodes}
    for f in activity.flows:
        if f.kind != "ObjectFlow":
            continue
        src = Endpoint.parse(f.source).node
        tgt = Endpoint.parse(f.target).node
        if src in nodes and tgt in nodes:
            adj[src].append(tgt)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in nodes}

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                raise ActivityValidationError(
                    f"Cycle detected in Activity {activity.name!r}: "
                    f"edge {u!r} -> {v!r}"
                )
            if color[v] == WHITE:
                dfs(v)
        color[u] = BLACK

    for n in nodes:
        if color[n] == WHITE:
            dfs(n)


def _endpoint_type(
    ep: Endpoint,
    activity: Activity,
    node_pins: dict[str, tuple[list[InputPin], list[OutputPin]]],
    *,
    is_output: bool,
) -> Type:
    """Type of a parsed endpoint.

    If ``is_output`` is True we are inspecting the endpoint as a wire
    source (so an unnamed endpoint on a parameter is the parameter's
    type); otherwise as a sink.
    """
    # Bare endpoint
    if ep.pin is None:
        # Parameter reference
        for p in activity.parameters:
            if p.id == ep.node:
                return p.type
        # Bare node reference: allowed only for Initial/Final-style Void
        # trigger wires.  Resolve to the single Void pin.
        if ep.node in node_pins:
            inputs, outputs = node_pins[ep.node]
            if is_output:
                for o in outputs:
                    if o.type is Type.VOID:
                        return o.type
            else:
                for i in inputs:
                    if i.type is Type.VOID:
                        return i.type
            raise ActivityValidationError(
                f"Bare endpoint {ep.node!r} is not Void-typed"
            )
        raise ActivityValidationError(
            f"Unknown endpoint {str(ep)!r} in Activity {activity.name!r}"
        )

    # Named pin
    inputs, outputs = node_pins[ep.node]
    if is_output:
        for o in outputs:
            if o.name == ep.pin:
                return o.type
        raise ActivityValidationError(
            f"Node {ep.node!r} has no output pin {ep.pin!r}"
        )
    for i in inputs:
        if i.name == ep.pin:
            return i.type
    raise ActivityValidationError(
        f"Node {ep.node!r} has no input pin {ep.pin!r}"
    )
