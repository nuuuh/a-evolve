"""ActivityRuntime — executes a validated ``Activity``.

Execution model:
  1. Validate once (catches type and structural errors up-front).
  2. Topologically sort the ObjectFlow graph.
  3. For each node: gather input values from its wired sources, invoke
     the node's body, write outputs into the run's output map.

Body dispatch:
  - ``Action``            → instantiate + ``execute(inputs, ctx)``
  - ``CallActivity``      → recurse: run referenced sub-Activity with
                            the incoming inputs as bindings
  - ``ExpansionRegion``   → iterate over ``items`` input; for each
                            element, recurse into the sub-Activity
                            with bindings{item_param: element, ...}
  - ``DecisionNode``      → route ``in`` onto ``true``/``false`` per guard
  - ``ForkNode`` / ``JoinNode`` → simple fan-out / fan-in
  - ``InitialNode`` / ``FinalNode`` → no-ops, emit/consume Void
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

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
from .flow import Endpoint
from .pin import InputPin, OutputPin
from .registry import ActionRegistry
from .spec import Activity, FlowSpec, NodeSpec
from .validator import _resolve_pins, validate

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Shared context threaded through every node's ``execute``.

    Intentionally small — workspace/git/config are explicit Activity
    parameters and should flow through wires, not globals.

    ``extra`` is a free-form escape hatch for the adapter layer (e.g.
    ``ActivityTemplate`` stores the ``NavigationEngine`` here so
    ``op.call_llm`` can reach its sandbox).  Nodes should prefer typed
    input pins over ``extra`` for anything user-facing.
    """

    registry: ActionRegistry
    runtime: "ActivityRuntime"
    logger: logging.Logger = field(default_factory=lambda: logger)
    trace: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class ActivityRuntime:
    """Runs ``Activity`` specs against a registry of node classes."""

    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    # ── Entry point ──────────────────────────────────────────────

    def run(
        self,
        activity: Activity,
        bindings: dict[str, Any],
        *,
        ctx: RunContext | None = None,
    ) -> dict[str, Any]:
        """Execute ``activity``.

        ``bindings`` maps parameter.id to a value.  Returns a dict whose
        keys are ``"node_id.pin"`` or plain parameter names.
        """
        if ctx is None:
            ctx = RunContext(registry=self.registry, runtime=self)
            validate(activity, self.registry)

        # Seed outputs with the incoming parameter values.
        outputs: dict[str, Any] = {}
        for p in activity.parameters:
            if p.direction == "in" and p.id in bindings:
                outputs[p.id] = bindings[p.id]

        # Topological order of nodes by ObjectFlow edges.
        order = _topo_order(activity, self.registry)

        for node_id in order:
            node_spec = _find_node(activity, node_id)
            self._execute_node(node_spec, activity, outputs, ctx)

        # Expose declared out-parameters at the top level.  An
        # out-parameter's value is delivered by a wire whose target is
        # the bare parameter id; resolve it once and copy into the
        # output map so callers can look it up by plain name.
        for p in activity.parameters:
            if p.direction == "out" and p.id not in outputs:
                resolved = _lookup_out_param(activity, outputs, p.id)
                if resolved is not None:
                    outputs[p.id] = resolved

        return outputs

    # ── Node dispatch ────────────────────────────────────────────

    def _execute_node(
        self,
        node_spec: NodeSpec,
        activity: Activity,
        outputs: dict[str, Any],
        ctx: RunContext,
    ) -> None:
        cls = self.registry.lookup(node_spec)
        inputs = self._gather_inputs(node_spec, activity, outputs, ctx)

        if cls is InitialNode:
            outputs[f"{node_spec.id}.out"] = None
            return
        if cls is FinalNode:
            return
        if cls is DecisionNode:
            guard = bool(inputs.get("guard"))
            datum = inputs.get("in")
            outputs[f"{node_spec.id}.true"] = datum if guard else None
            outputs[f"{node_spec.id}.false"] = None if guard else datum
            return
        if cls is ForkNode:
            value = inputs.get("in")
            n = int(node_spec.config.get("outputs", 2))
            for i in range(n):
                outputs[f"{node_spec.id}.out{i}"] = value
            return
        if cls is JoinNode:
            # Synchronises: emits the first non-None input (values must
            # be identical by contract — UML JoinNode assumes coherent
            # tokens).  Accept any for simplicity.
            n = int(node_spec.config.get("inputs", 2))
            out_value = None
            for i in range(n):
                v = inputs.get(f"in{i}")
                if v is not None:
                    out_value = v
                    break
            outputs[f"{node_spec.id}.out"] = out_value
            return
        if cls is CallActivity:
            sub = activity.sub_activities[node_spec.config["activity"]]
            sub_outputs = self.run(sub, inputs, ctx=ctx)
            for p in sub.parameters:
                if p.direction != "out":
                    continue
                value = _lookup_out_param(sub, sub_outputs, p.id)
                outputs[f"{node_spec.id}.{p.id}"] = value
            ctx.trace.append({"node": node_spec.id, "kind": "CallActivity"})
            return
        if cls is ExpansionRegion:
            self._run_expansion(node_spec, activity, inputs, outputs, ctx)
            return

        # Concrete Action
        node: ActivityNode = cls(node_spec.config)
        produced = node.execute(inputs, ctx)  # type: ignore[attr-defined]
        for pin_name, value in produced.items():
            outputs[f"{node_spec.id}.{pin_name}"] = value
        ctx.trace.append({"node": node_spec.id, "kind": "Action"})

    # ── ExpansionRegion ──────────────────────────────────────────

    def _run_expansion(
        self,
        node_spec: NodeSpec,
        activity: Activity,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        ctx: RunContext,
    ) -> None:
        sub_name = node_spec.config["activity"]
        sub = activity.sub_activities[sub_name]
        mode = node_spec.config.get("mode", "iterative")
        item_param = node_spec.config.get("item_param", "item")
        result_param = node_spec.config.get("result_param", "")

        items = inputs.get("items") or []

        # Per-item binding: fixed inputs + item
        fixed = {k: v for k, v in inputs.items() if k != "items"}

        def run_one(element: Any) -> dict[str, Any]:
            binding = dict(fixed)
            binding[item_param] = element
            return self.run(sub, binding, ctx=ctx)

        if mode == "parallel" and len(items) > 1:
            with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
                results = list(pool.map(run_one, items))
        else:
            results = [run_one(e) for e in items]

        # Expose collected results on this region's output pins.
        if result_param:
            collected = [_lookup_out_param(sub, r, result_param) for r in results]
            outputs[f"{node_spec.id}.results"] = collected

        # Non-result out-parameters: we expose the *last* element's value
        # for non-list out-params.  This matches UML "output pin per
        # element" semantics pragmatically for the rare non-result
        # output case.
        for p in sub.parameters:
            if p.direction != "out" or p.id == result_param:
                continue
            last = results[-1] if results else {}
            outputs[f"{node_spec.id}.{p.id}"] = _lookup_out_param(sub, last, p.id)

        ctx.trace.append({
            "node": node_spec.id,
            "kind": "ExpansionRegion",
            "items": len(items),
            "mode": mode,
        })

    # ── Input gathering ──────────────────────────────────────────

    def _gather_inputs(
        self,
        node_spec: NodeSpec,
        activity: Activity,
        outputs: dict[str, Any],
        ctx: RunContext,
    ) -> dict[str, Any]:
        """Resolve each input pin of a node by walking its incoming wires."""
        input_pins, _ = _resolve_pins(node_spec, activity, self.registry)
        gathered: dict[str, Any] = {}
        for pin in input_pins:
            for f in activity.flows:
                if f.kind != "ObjectFlow":
                    continue
                target = Endpoint.parse(f.target)
                if target.node == node_spec.id and target.pin == pin.name:
                    src = Endpoint.parse(f.source)
                    gathered[pin.name] = _resolve_value(src, outputs)
                    break
        return gathered


def _resolve_value(src: Endpoint, outputs: dict[str, Any]) -> Any:
    """Look up the value flowing from an endpoint."""
    key = f"{src.node}.{src.pin}" if src.pin else src.node
    if key in outputs:
        return outputs[key]
    return outputs.get(src.node)


def _lookup_out_param(activity: Activity, outputs: dict[str, Any], name: str) -> Any:
    """Value delivered to an out-parameter of an Activity.

    Out-parameters receive their value via a wire whose target is the
    bare parameter id.  We find the wire and return its source value.
    """
    for f in activity.flows:
        if f.kind != "ObjectFlow":
            continue
        tgt = Endpoint.parse(f.target)
        if tgt.node == name and tgt.pin is None:
            return _resolve_value(Endpoint.parse(f.source), outputs)
    # Fallback: perhaps an inner node wrote to the parameter id directly.
    return outputs.get(name)


def _topo_order(activity: Activity, registry: ActionRegistry) -> list[str]:
    """Kahn's algorithm over ObjectFlows + ControlFlows."""
    indeg: dict[str, int] = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)
    nodes = [n.id for n in activity.nodes]
    node_set = set(nodes)

    for n in nodes:
        indeg[n] = indeg.get(n, 0)

    for f in activity.flows:
        src_node = Endpoint.parse(f.source).node
        tgt_node = Endpoint.parse(f.target).node
        if src_node in node_set and tgt_node in node_set:
            adj[src_node].append(tgt_node)
            indeg[tgt_node] += 1

    q: deque[str] = deque([n for n in nodes if indeg[n] == 0])
    order: list[str] = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(nodes):
        raise RuntimeError(
            f"Cycle in Activity {activity.name!r} — validator should have "
            f"caught this"
        )
    return order


def _find_node(activity: Activity, node_id: str) -> NodeSpec:
    for n in activity.nodes:
        if n.id == node_id:
            return n
    raise KeyError(f"Node {node_id!r} not found in Activity {activity.name!r}")
