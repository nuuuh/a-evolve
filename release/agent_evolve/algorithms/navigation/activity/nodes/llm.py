"""LLM actions.

Two variants:

  ``op.call_llm``         — sandboxed call via ``AEvolveEngine._run_llm``;
                            used when the evolver needs full bash access
                            inside a Docker sandbox.  Requires ``engine``
                            in the RunContext (set by ``ActivityTemplate``).

  ``op.call_llm_simple``  — a single-turn completion against a bare
                            ``BedrockProvider``.  Used for analyst/critic
                            roles that don't need tool access.

Both are thin wrappers — they do not duplicate sandbox lifecycle or
prompt-building logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..action import Action
from ..pin import InputPin, OutputPin
from ..types import Type

logger = logging.getLogger(__name__)


class CallLLM(Action):
    """Call the evolver LLM with sandboxed bash tool access.

    Requires ``ctx.extra["engine"]`` to be a ``NavigationEngine`` /
    ``AEvolveEngine`` instance.  ``ActivityTemplate`` sets this up
    automatically when it constructs the runtime.
    """

    action_kind = "op.call_llm"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="prompt", type=Type.PROMPT_TEXT),
            InputPin(name="workspace", type=Type.WORKSPACE),
            InputPin(name="config", type=Type.CONFIG),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="response", type=Type.LLM_RESPONSE)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        engine = getattr(ctx, "extra", {}).get("engine")
        if engine is None:
            raise RuntimeError(
                "op.call_llm requires an engine in ctx.extra — did you "
                "forget to construct this runtime via ActivityTemplate?"
            )
        ws = inputs["workspace"]
        cfg = inputs["config"]

        disabled = [
            name for name, on in [
                ("prompts", cfg.evolve_prompts),
                ("skills", cfg.evolve_skills),
                ("memory", cfg.evolve_memory),
                ("tools", cfg.evolve_tools),
                ("infra", cfg.evolve_infra),
            ]
            if not on
        ]
        with ws.protect(disabled):
            result = engine._run_llm(inputs["prompt"], ws.root)
        return {"response": result}


class CallLLMSimple(Action):
    """Single-turn LLM completion, no tools, no sandbox.

    Used by analyst/critic roles that only need to read a prompt and
    emit text.  Requires ``ctx.extra["engine"]`` to have an ``llm``
    attribute that is a ``BedrockProvider``-compatible instance.
    """

    action_kind = "op.call_llm_simple"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="prompt", type=Type.PROMPT_TEXT),
            InputPin(name="config", type=Type.CONFIG),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="response", type=Type.LLM_RESPONSE)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        engine = getattr(ctx, "extra", {}).get("engine")
        if engine is None or getattr(engine, "llm", None) is None:
            # Graceful fallback for tests: emit an empty response.
            return {"response": {"content": "", "usage": {}, "conversation": []}}

        system_prompt = self.config.get(
            "system_prompt",
            "You are an expert assistant. Respond concisely.",
        )
        max_tokens = int(self.config.get("max_tokens", 4096))
        temperature = float(self.config.get("temperature", 0.0))

        try:
            from .....llm.bedrock import BedrockProvider

            if isinstance(engine.llm, BedrockProvider):
                response = engine.llm.converse_loop(
                    system_prompt=system_prompt,
                    user_message=inputs["prompt"],
                    tools=[],
                    tool_executor={},
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return {
                    "response": {
                        "content": response.content,
                        "usage": response.usage,
                        "conversation": getattr(response, "raw", {}).get(
                            "conversation", []
                        ),
                    }
                }
        except Exception as e:
            logger.warning("op.call_llm_simple failed: %s", e)
        return {"response": {"content": "", "usage": {}, "conversation": []}}


class ParsePlan(Action):
    """Extract a JSON plan from the analyst's LLM response.

    Matches the parsing rules in ``AnalystRole._parse_plan``.
    """

    action_kind = "op.parse_plan"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="response", type=Type.LLM_RESPONSE)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="plan", type=Type.PLAN)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        import re

        text = (inputs["response"] or {}).get("content", "") or ""
        for m in re.finditer(r"\{.*\}", text, re.DOTALL):
            try:
                plan = json.loads(m.group(0))
            except (json.JSONDecodeError, ValueError):
                continue
            if "main_evolution" in plan or "branches" in plan:
                plan.setdefault("summary", "")
                plan.setdefault("main_evolution", {})
                plan.setdefault("branches", [])
                return {"plan": plan}
        return {"plan": {"summary": "", "main_evolution": {}, "branches": []}}


BUILTINS = [CallLLM, CallLLMSimple, ParsePlan]
