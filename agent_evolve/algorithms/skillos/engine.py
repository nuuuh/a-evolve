"""SkillOSEngine — adapted from Ouyang et al. (2025).

Implements the SkillOS skill-curation framework: a hierarchical skill
registry where an LLM-based curator creates, selects, refines, and
retires skills based on task outcomes.

The original uses RL-trained curator policies; we approximate with an
LLM-based curator (same model as all other baselines) for fair comparison.
The key innovation preserved: hierarchical Domain → Family → Skill
organization with lazy loading and skill-level effectiveness tracking.

Reference: https://github.com/EvolvingAgentsLabs/skillos
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


CURATOR_TEMPLATE = """You are a skill curator for an AI agent operating on a long-running task stream.

Your job: analyze recent task outcomes and maintain a hierarchical skill library that helps the agent solve future tasks more effectively.

## Current Skill Registry
{registry}

## Skill Effectiveness Log
{effectiveness_log}

## Recent Task Outcomes (batch {cycle})
{trajectory_summary}

## Curation Tasks

1. **Create skills**: Identify successful solving patterns that should be codified as reusable skills. Each skill is a markdown document with: name, domain, description, and step-by-step instructions.

2. **Refine skills**: If existing skills were used but underperformed, improve their content based on what worked in the trajectories.

3. **Retire skills**: Remove skills that have been tried multiple times with consistently poor results.

4. **Update effectiveness**: Track which skills are working (success_count / use_count).

## Skill Format

Each skill is a markdown file stored at `skills/<domain>/<name>.md` with:
```
# <Skill Name>
Domain: <domain>
Effectiveness: <low|medium|high>
Uses: <count>
Successes: <count>

## When to use
<conditions under which this skill applies>

## Steps
<step-by-step instructions the solver should follow>
```

## Output Format

Respond with ONLY a JSON object (no markdown fences):
{{
  "analysis": "brief summary of what you observed",
  "create": [
    {{
      "name": "skill_name",
      "domain": "domain_category",
      "description": "when to use this skill",
      "steps": "step-by-step instructions"
    }}
  ],
  "refine": [
    {{
      "name": "existing_skill_name",
      "domain": "domain_category",
      "description": "updated description",
      "steps": "improved steps"
    }}
  ],
  "retire": ["skill_name_to_remove"],
  "effectiveness": [
    {{"name": "skill_name", "used": true, "succeeded": true}}
  ]
}}"""


class SkillOSEngine(EvolutionEngine):
    """Hierarchical skill curation engine adapted from SkillOS.

    Each cycle the curator LLM:
    1. Reviews the skill registry and recent task outcomes
    2. Creates new skills from successful patterns
    3. Refines underperforming skills
    4. Retires consistently failing skills
    5. Tracks per-skill effectiveness

    Skills are stored as markdown files in the workspace's skills/ directory,
    organized by domain (matching SkillOS's Domain → Family → Skill hierarchy).
    """

    def __init__(self, config: EvolveConfig, llm: LLMProvider | None = None):
        self.config = config
        self._llm = llm
        self._effectiveness: dict[str, dict[str, int]] = {}

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
        """Run the curator to maintain the skill registry."""
        cycle_num = history.latest_cycle + 1
        recent_obs = history.get_observations(last_n_cycles=2)
        trajectory_summary = self._format_trajectories(recent_obs)

        if not trajectory_summary.strip():
            logger.info("SkillOS: no trajectories, skipping")
            return StepResult(mutated=False)

        registry = self._build_registry_overview(workspace)
        effectiveness_log = self._build_effectiveness_log()

        prompt = CURATOR_TEMPLATE.format(
            registry=registry,
            effectiveness_log=effectiveness_log,
            trajectory_summary=trajectory_summary,
            cycle=cycle_num,
        )

        response = self.llm.generate(prompt)
        recommendations = self._parse_json(response)
        if not recommendations:
            return StepResult(mutated=False)

        mutated = False

        for spec in recommendations.get("create", []):
            if self._create_skill(workspace, spec):
                mutated = True

        for spec in recommendations.get("refine", []):
            if self._refine_skill(workspace, spec):
                mutated = True

        for name in recommendations.get("retire", []):
            if self._retire_skill(workspace, name):
                mutated = True

        for entry in recommendations.get("effectiveness", []):
            self._update_effectiveness(entry)

        logger.info("SkillOS cycle %d: mutated=%s", cycle_num, mutated)
        return StepResult(mutated=mutated)

    def _create_skill(self, workspace: AgentWorkspace, spec: dict) -> bool:
        """Create a new skill in the registry."""
        name = spec.get("name", "").strip()
        domain = spec.get("domain", "general").strip()
        description = spec.get("description", "").strip()
        steps = spec.get("steps", "").strip()
        if not name or not steps:
            return False

        content = f"""# {name}
Domain: {domain}
Effectiveness: medium
Uses: 0
Successes: 0

## When to use
{description}

## Steps
{steps}
"""
        skill_name = f"{domain}/{name}".replace(" ", "_").lower()
        workspace.write_skill(skill_name, content)
        self._effectiveness[name] = {"uses": 0, "successes": 0}
        logger.info("SkillOS: created skill '%s' in domain '%s'", name, domain)
        return True

    def _refine_skill(self, workspace: AgentWorkspace, spec: dict) -> bool:
        """Update an existing skill's content."""
        name = spec.get("name", "").strip()
        domain = spec.get("domain", "general").strip()
        description = spec.get("description", "").strip()
        steps = spec.get("steps", "").strip()
        if not name or not steps:
            return False

        eff = self._effectiveness.get(name, {"uses": 0, "successes": 0})
        content = f"""# {name}
Domain: {domain}
Effectiveness: medium
Uses: {eff['uses']}
Successes: {eff['successes']}

## When to use
{description}

## Steps
{steps}
"""
        skill_name = f"{domain}/{name}".replace(" ", "_").lower()
        workspace.write_skill(skill_name, content)
        logger.info("SkillOS: refined skill '%s'", name)
        return True

    def _retire_skill(self, workspace: AgentWorkspace, name: str) -> bool:
        """Remove a skill from the registry."""
        name = name.strip()
        if not name:
            return False
        if workspace.skill_exists(name):
            workspace.remove_skill(name)
            self._effectiveness.pop(name, None)
            logger.info("SkillOS: retired skill '%s'", name)
            return True
        return False

    def _update_effectiveness(self, entry: dict) -> None:
        """Track skill usage and success."""
        name = entry.get("name", "").strip()
        if not name:
            return
        if name not in self._effectiveness:
            self._effectiveness[name] = {"uses": 0, "successes": 0}
        if entry.get("used"):
            self._effectiveness[name]["uses"] += 1
        if entry.get("succeeded"):
            self._effectiveness[name]["successes"] += 1

    def _build_registry_overview(self, workspace: AgentWorkspace) -> str:
        """Build a summary of the current skill registry."""
        skills = workspace.list_skills()
        if not skills:
            return "(empty registry — no skills created yet)"
        lines = []
        for s in skills:
            eff = self._effectiveness.get(s.name, {})
            uses = eff.get("uses", 0)
            successes = eff.get("successes", 0)
            rate = f"{successes}/{uses}" if uses > 0 else "untested"
            lines.append(f"- {s.name} [{rate}]: {s.content[:80]}...")
        return "\n".join(lines)

    def _build_effectiveness_log(self) -> str:
        """Build a summary of skill effectiveness tracking."""
        if not self._effectiveness:
            return "(no effectiveness data yet)"
        lines = []
        for name, data in sorted(self._effectiveness.items()):
            uses = data["uses"]
            successes = data["successes"]
            rate = f"{successes}/{uses} ({100*successes//uses}%)" if uses > 0 else "unused"
            lines.append(f"- {name}: {rate}")
        return "\n".join(lines)

    def _format_trajectories(self, observations: list[Observation]) -> str:
        """Format observations into a trajectory summary."""
        if not observations:
            return ""
        lines = []
        for obs in observations[-30:]:
            status = "PASS" if obs.success else "FAIL"
            detail = obs.detail[:200] if obs.detail else ""
            lines.append(f"[{status}] {obs.task_id}: {detail}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Any:
        """Parse JSON from LLM response."""
        if not text:
            return None
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            if start >= 0:
                try:
                    return json.loads(text[start:])
                except json.JSONDecodeError:
                    pass
            logger.warning("SkillOS: failed to parse JSON response")
            return None
