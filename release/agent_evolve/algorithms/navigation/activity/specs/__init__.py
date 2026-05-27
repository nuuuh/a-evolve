"""Reference Activity specs — 1:1 with the existing evolution templates.

Each spec is constructed in Python using ``ActivityBuilder`` and
serialised to JSON on demand.  Keeping the construction code alongside
the JSON file lets us re-generate specs after any catalog change
without hand-editing JSON.

``build_inline_activity()``       ≡ ``InlineTemplate.execute``
``build_plan_driven_activity()``  ≡ ``OrchestratedTemplate`` + PlanDriven
"""

from __future__ import annotations

from .inline import build_inline_activity
from .plan_driven import build_plan_driven_activity

__all__ = ["build_inline_activity", "build_plan_driven_activity"]
