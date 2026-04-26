# Goal Tracker

<!--
This file tracks the ultimate goal, acceptance criteria, and plan evolution.
It prevents goal drift by maintaining a persistent anchor across all rounds.

RULES:
- IMMUTABLE SECTION: Do not modify after initialization
- MUTABLE SECTION: Update each round, but document all changes
- Every task must be in one of: Active, Completed, or Deferred
- Deferred items require explicit justification
-->

## IMMUTABLE SECTION
<!-- Do not modify after initialization -->

### Ultimate Goal

Implement five diverse multi-agent evolution templates for the A-Evolve
system that beat single-agent evolution (42.9%) on FutureX, produce
functional web-search tools (>80% network success rate), and demonstrate
that the solver actively uses evolved tools to improve predictions
(batch 2+ pass rate > batch 1).

### Acceptance Criteria
<!-- Each criterion must be independently verifiable -->

- **AC1**: `mosaic` template implemented, imports cleanly, passes a 4-task pipeline test showing planner → N evolvers → fusion agent trajectory steps.
- **AC2**: `adaptive` template implemented, imports cleanly, passes a 4-task pipeline test showing deterministic state-based dispatch (no LLM planner) with role-specific trajectory steps.
- **AC3**: YAML configs (`mosaic_evo.yaml`, `adaptive_evo.yaml`) exist and resolve `orchestrator:` key correctly via the dynamic loader.
- **AC4**: All 5 templates (verified, debate, parallel_specialists, mosaic, adaptive) import without errors; `python -m pytest tests/` passes with no regressions (186+ tests).
- **AC5**: At least one template produces a 4-task end-to-end trajectory with `mutated=True` and tools written to registry.

---

## MUTABLE SECTION
<!-- Update each round with justification for changes -->

### Plan Version: 1 (Updated: Round 0)

#### Plan Evolution Log
<!-- Document any changes to the plan with justification -->
| Round | Change | Reason | Impact on AC |
|-------|--------|--------|--------------|
| 0 | Initial plan + full implementation | - | All ACs addressed |

#### Active Tasks
<!-- Map each task to its target Acceptance Criterion and routing tag -->
| Task | Target AC | Status | Tag | Owner | Notes |
|------|-----------|--------|-----|-------|-------|
| (all tasks completed — see below) | - | - | - | - | - |

### Completed and Verified
<!-- Only move tasks here after Codex verification -->
| AC | Task | Completed Round | Verified Round | Evidence |
|----|------|-----------------|----------------|----------|
| AC1 | Implement `mosaic` template | 0 | pending | `templates/mosaic.py` created; 4-task pipeline: plan→specialist(main,mutated=True)→fusion |
| AC2 | Implement `adaptive` template | 0 | pending | `templates/adaptive.py` created; 4-task pipeline: state_inspection(tools=0)→tool_builder(mutated=True) |
| AC3 | Create `mosaic_evo.yaml` + `adaptive_evo.yaml` | 0 | pending | Both configs created, `orchestrator:` key resolves correctly |
| AC3 | Dynamic loader in `solve_all_with_evolution.py` | 0 | pending | Already implemented in prior session; tested with all 5 templates |
| AC4 | All 5 templates import + 186 tests pass | 0 | pending | `python -m pytest tests/` → 186 passed; all 5 templates import cleanly |
| AC5 | Pipeline test: mosaic `mutated=True` | 0 | pending | Trajectory: specialist main mutated=True, 4 tools in registry |
| AC5 | Pipeline test: adaptive `mutated=True` | 0 | pending | Trajectory: tool_builder mutated=True, 4 tools + 3 memories created |

### Explicitly Deferred
<!-- Items here require strong justification -->
| Task | Original AC | Deferred Since | Justification | When to Reconsider |
|------|-------------|----------------|---------------|-------------------|

### Open Issues
<!-- Issues discovered during implementation -->
| Issue | Discovered Round | Blocking AC | Resolution Path |
|-------|-----------------|-------------|-----------------|
