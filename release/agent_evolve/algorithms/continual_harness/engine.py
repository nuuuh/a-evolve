"""ContinualHarnessEngine — adapted from Karten et al. (2025).

Implements the Continual Harness evolution strategy: four independent
refinement passes (prompt, skills, memory, tools) that analyze recent
trajectories and apply CRUD operations to the workspace.

The original framework interleaves refinement with action during a single
deployment episode. We adapt to our between-batch evolution loop: the
engine runs all four passes after each batch completes, using the same
LLM and tool budget as other baselines.

Reference: https://github.com/sethkarten/continual-harness
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...config import EvolveConfig
from ...contract.workspace import AgentWorkspace
from ...engine.base import EvolutionEngine
from ...engine.history import EvolutionHistory
from ...engine.trial import TrialRunner
from ...llm.base import LLMProvider
from ..aevolve.tools import create_default_llm
from ...types import Observation, StepResult

logger = logging.getLogger(__name__)


PROMPT_EVOLUTION_TEMPLATE = """You are a harness refinement system analyzing an AI agent's recent task-solving trajectories.

Your job: rewrite the agent's system prompt to improve performance on future tasks based on what went wrong and right.

## Current System Prompt
{current_prompt}

## Recent Trajectories (batch {cycle})
{trajectory_summary}

## Instructions
Analyze the trajectories for:
1. Patterns where the agent failed — what instructions would prevent these?
2. Patterns where the agent succeeded — what instructions should be reinforced?
3. Missing guidance — what domain knowledge should be added?

Output ONLY the complete new system prompt (no explanation, no markdown fences). If no changes needed, output the current prompt unchanged."""


SKILL_EVOLUTION_TEMPLATE = """You are a harness refinement system analyzing an AI agent's recent task-solving trajectories.

Your job: identify reusable skills to add, update, or retire based on what the agent did.

## Current Skills
{skill_overview}

## Recent Trajectories (batch {cycle})
{trajectory_summary}

## Instructions
1. Identify successful multi-step patterns that should be saved as reusable skills
2. Identify skills that failed repeatedly and should be updated or retired
3. Identify missing capabilities that new skills could address

Output a JSON object (no markdown fences):
{{
  "analysis": "brief summary",
  "add": [{{"name": "string", "content": "skill content as markdown"}}],
  "update": [{{"name": "existing_skill_name", "content": "updated content"}}],
  "retire": ["skill_name_to_remove"]
}}"""


MEMORY_EVOLUTION_TEMPLATE = """You are a harness refinement system analyzing an AI agent's recent task-solving trajectories.

Your job: extract lessons learned that should be stored in memory for future tasks.

## Current Memory
{memory_overview}

## Recent Trajectories (batch {cycle})
{trajectory_summary}

## Instructions
Extract up to 5 concise, actionable lessons from the trajectories. Focus on:
1. Domain-specific knowledge discovered during solving
2. Error patterns to avoid in the future
3. Successful strategies worth remembering

Output a JSON array of memory entries (no markdown fences):
[{{"key": "short_id", "content": "the lesson learned"}}]"""


TOOL_EVOLUTION_TEMPLATE = """You are a harness refinement system analyzing an AI agent's recent task-solving trajectories.

Your job: recommend changes to the agent's tool registry based on what tools were needed but missing, or what tools failed.

## Current Tool Registry
{tool_overview}

## Recent Trajectories (batch {cycle})
{trajectory_summary}

## Instructions
1. Identify tool calls that failed or tools the agent needed but didn't have
2. Recommend new tool registrations or updates to existing ones
3. Do NOT recommend removing core tools

Output a JSON object (no markdown fences):
{{
  "analysis": "brief summary",
  "updates": [{{"tool_name": "string", "description": "string", "action": "add|update|remove"}}]
}}

If no changes needed, output: {{"analysis": "no changes needed", "updates": []}}"""


class ContinualHarnessEngine(EvolutionEngine):
    """Four-pass CRUD harness evolution adapted from Continual Harness.

    Each cycle runs four independent refinement passes:
    1. Prompt: rewrite the system prompt based on trajectory analysis
    2. Skills: create/update/retire skills based on successful patterns
    3. Memory: extract lessons learned into persistent memory
    4. Tools: update tool registry based on missing/failing tools

    Each pass is independent — if one fails, the others still run.
    """

    def __init__(self, config: EvolveConfig, llm: LLMProvider | None = None):
        self.config = config
        self._llm = llm

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = create_default_llm(self.config)
        return self._llm

    def step(
        self,
        workspace: AgentWorkspace,
        observations: list[Observation],
        history: EvolutionHistory,
        trial: TrialRunner,
    ) -> StepResult:
        """Run four independent refinement passes on the workspace."""
        cycle_num = history.latest_cycle + 1
        recent_obs = history.get_observations(last_n_cycles=2)
        trajectory_summary = self._format_trajectories(recent_obs)

        if not trajectory_summary.strip():
            logger.info("ContinualHarness: no trajectories, skipping")
            return StepResult(mutated=False)

        results = {}
        mutated = False

        for name, fn in [
            ("prompt", lambda: self._evolve_prompt(workspace, trajectory_summary, cycle_num)),
            ("skills", lambda: self._evolve_skills(workspace, trajectory_summary, cycle_num)),
            ("memory", lambda: self._evolve_memory(workspace, trajectory_summary, cycle_num)),
            ("tools", lambda: self._evolve_tools(workspace, trajectory_summary, cycle_num)),
        ]:
            if not self._pass_enabled(name):
                continue
            try:
                changed = fn()
                results[name] = changed
                if changed:
                    mutated = True
            except Exception as e:
                logger.error("ContinualHarness pass '%s' failed: %s", name, e, exc_info=True)
                results[name] = False

        logger.info("ContinualHarness cycle %d results: %s", cycle_num, results)
        return StepResult(mutated=mutated)

    def _pass_enabled(self, name: str) -> bool:
        """Check if a pass is enabled by config."""
        mapping = {
            "prompt": self.config.evolve_prompts,
            "skills": self.config.evolve_skills,
            "memory": self.config.evolve_memory,
            "tools": self.config.evolve_tools,
        }
        return mapping.get(name, True)

    def _evolve_prompt(self, workspace: AgentWorkspace, trajectories: str, cycle: int) -> bool:
        """Rewrite the system prompt based on trajectory analysis."""
        current_prompt = workspace.read_prompt()
        prompt = PROMPT_EVOLUTION_TEMPLATE.format(
            current_prompt=current_prompt,
            trajectory_summary=trajectories,
            cycle=cycle,
        )
        response = self.llm.generate(prompt)
        if response and response.strip() != current_prompt.strip():
            workspace.write_prompt(response.strip())
            logger.info("ContinualHarness: prompt rewritten (cycle %d)", cycle)
            return True
        return False

    def _evolve_skills(self, workspace: AgentWorkspace, trajectories: str, cycle: int) -> bool:
        """Create/update/retire skills based on trajectory patterns."""
        skills = workspace.list_skills()
        skill_overview = "\n".join(f"- {s.name}: {s.content[:100]}..." for s in skills) or "(empty)"

        prompt = SKILL_EVOLUTION_TEMPLATE.format(
            skill_overview=skill_overview,
            trajectory_summary=trajectories,
            cycle=cycle,
        )
        response = self.llm.generate(prompt)
        recommendations = self._parse_json(response)
        if not recommendations:
            return False

        changed = False
        for spec in recommendations.get("add", []):
            name = spec.get("name", "").strip()
            content = spec.get("content", "").strip()
            if name and content:
                workspace.write_skill(name, content)
                changed = True

        for spec in recommendations.get("update", []):
            name = spec.get("name", "").strip()
            content = spec.get("content", "").strip()
            if name and content:
                workspace.write_skill(name, content)
                changed = True

        for name in recommendations.get("retire", []):
            if name and workspace.skill_exists(name):
                workspace.remove_skill(name)
                changed = True

        return changed

    def _evolve_memory(self, workspace: AgentWorkspace, trajectories: str, cycle: int) -> bool:
        """Extract lessons learned into persistent memory."""
        memories = workspace.read_all_memories(limit=50)
        memory_overview = "\n".join(f"- {m}" for m in memories[:20]) or "(empty)"

        prompt = MEMORY_EVOLUTION_TEMPLATE.format(
            memory_overview=memory_overview,
            trajectory_summary=trajectories,
            cycle=cycle,
        )
        response = self.llm.generate(prompt)
        entries = self._parse_json(response)
        if not entries or not isinstance(entries, list):
            return False

        changed = False
        for entry in entries[:5]:
            if isinstance(entry, dict) and entry.get("content"):
                workspace.append_memory(entry["content"])
                changed = True

        return changed

    def _evolve_tools(self, workspace: AgentWorkspace, trajectories: str, cycle: int) -> bool:
        """Update tool registry based on trajectory analysis."""
        tool_registry = workspace.read_tool_registry()
        prompt = TOOL_EVOLUTION_TEMPLATE.format(
            tool_overview=tool_registry or "(empty)",
            trajectory_summary=trajectories,
            cycle=cycle,
        )
        response = self.llm.generate(prompt)
        recommendations = self._parse_json(response)
        if not recommendations or not recommendations.get("updates"):
            return False

        changed = False
        for update in recommendations.get("updates", []):
            action = update.get("action", "")
            tool_name = update.get("tool_name", "")
            if action == "add" and tool_name:
                workspace.register_tool(tool_name, update.get("description", ""))
                changed = True

        return changed

    def _format_trajectories(self, observations: list[Observation]) -> str:
        """Format observations into a trajectory summary for LLM analysis."""
        if not observations:
            return ""
        lines = []
        for obs in observations[-30:]:
            status = "PASS" if obs.success else "FAIL"
            detail = obs.detail[:200] if obs.detail else ""
            lines.append(f"[{status}] {obs.task_id}: {detail}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Any:
        """Parse JSON from LLM response, handling markdown fences."""
        if not text:
            return None
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{") if "{" in text else text.find("[")
            if start >= 0:
                try:
                    return json.loads(text[start:])
                except json.JSONDecodeError:
                    pass
            logger.warning("ContinualHarness: failed to parse JSON response")
            return None
