"""Critic agent — stub sub-Activity.

Placeholder for a future critic role.  Takes a ``MutationReport``, calls
an LLM to produce an approval verdict.  Not yet used by any shipped
spec; provided so third-party specs can reference ``critic`` without
building it themselves.
"""

from __future__ import annotations

from ...builder import ActivityBuilder
from ...spec import Activity
from ...types import Type


def build_critic_activity() -> Activity:
    return (
        ActivityBuilder("critic", description="Review a mutation; emit a verdict.")
        .parameter("report", Type.MUTATION_REPORT, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("response", Type.LLM_RESPONSE, direction="out")
        .action("call", "op.call_llm_simple")
        # Minimal wiring: critic reads cfg + a placeholder prompt (empty
        # string).  Users composing a real critic will extend this.
        .object_flow("cfg", "call.config")
        .object_flow("call.response", "response")
        .build_unchecked()
    )
