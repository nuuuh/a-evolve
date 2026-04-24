"""Navigation-specific actions.

Wrap navigation-only helpers (read branch leaves, extract plan branches,
read routing history).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..action import Action
from ..pin import InputPin, OutputPin
from ..types import Type


class ReadBranchLeaves(Action):
    """Summarise each branch's workspace state (prompt, skills, tools, readme).

    Delegates to ``NavigationEngine._read_branch_leaves``.  Emitted as a
    text blob; callers can embed it in a prompt.
    """

    action_kind = "op.read_branch_leaves"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="workspace", type=Type.WORKSPACE),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="summary", type=Type.STRING)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from ...engine import NavigationEngine

        _, tree = inputs["git"]
        ws = inputs["workspace"]
        nav = NavigationEngine(config=None, llm=None)
        viable = [b.name for b in tree.branches]
        summaries = nav._read_branch_leaves(tree, ws.root, viable)
        return {"summary": json.dumps(summaries, indent=2, default=str)}


class ExtractPlanBranches(Action):
    """Pull the ``branches`` list out of a Plan dict."""

    action_kind = "op.extract_plan_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="plan", type=Type.PLAN)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="branches", type=Type.BRANCH_SPEC_LIST)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        plan = inputs["plan"] or {}
        return {"branches": list(plan.get("branches", []))}


class LoadRoutingHistory(Action):
    """Read the routing-log JSONL into a list.  Empty if file missing."""

    action_kind = "op.load_routing_history"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="path", type=Type.STRING, required=False)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="history", type=Type.STRING_LIST)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        raw = inputs.get("path") or ""
        history: list[dict[str, Any]] = []
        if raw:
            p = Path(raw)
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.strip():
                        try:
                            history.append(json.loads(line))
                        except Exception:
                            pass
        # Stored as STRING_LIST (list of JSON strings) is wrong; use the
        # raw list — the pin nominal type is STRING_LIST but runtime
        # treats value as opaque.
        return {"history": history}


BUILTINS = [ReadBranchLeaves, ExtractPlanBranches, LoadRoutingHistory]
