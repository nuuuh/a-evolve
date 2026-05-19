"""SkillOS evolution engine (Ouyang et al., 2025).

Ports the skill curation framework from SkillOS: a hierarchical skill
registry with LLM-based creation, selection, and retirement of skills
based on task outcomes.
"""

from .engine import SkillOSEngine

__all__ = ["SkillOSEngine"]
