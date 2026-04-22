"""Navigation -- decoupled evolution with agentic branch routing.

Promoted from ``aevolve/navigation.py`` to a peer-package so it stands
alongside ``aevolve``, ``mas_adaptive_skill``, ``meta_harness``, ``gepa``.
"""

from .engine import NavigationEngine
from .prompts import (
    ANALYZE_PLAN_SYSTEM_PROMPT,
    NAVIGATE_SYSTEM_PROMPT,
    build_analyze_plan_prompt,
    build_navigate_prompt,
)

__all__ = [
    "NavigationEngine",
    "ANALYZE_PLAN_SYSTEM_PROMPT",
    "NAVIGATE_SYSTEM_PROMPT",
    "build_analyze_plan_prompt",
    "build_navigate_prompt",
]
