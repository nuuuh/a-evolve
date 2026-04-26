# Ask Codex Input

## Question

You are reviewing the CANDIDATE PLAN v1 for a codebase review of A-EVOLVE, an agent evolution framework. The review scope is: PolyBench, CTF-Dojo, FutureX benchmarks, focusing on navigation (branching) and multi-agent orchestration contributions.

CANDIDATE FINDINGS (aggregated from Claude analysis):

CRITICAL:
1. FutureX solver does its own evaluation with limited answer extraction (boxed only) instead of calling benchmark.evaluate(). Benchmark has 5+ fallback patterns. Impact: incorrect scoring signal to evolver.
2. workspace_root missing from args_dict in solve_all_with_evolution.py line ~416-424. Workers never get the path, so evolved infra/ scripts (search_pipeline.py, submit_handler.py) are never used. Breaks the entire infra layer evolution.
3. StrategyTree.to_dict() omits failed_checkouts field (types.py line 159-167). After serialization/deserialization, counters reset to 0. Branch filtering mechanism is dead.
4. failed_checkouts counter is never incremented anywhere — the filtering mechanism is defined but never triggered.

HIGH:
5. Observer reveal gate uses instance_id vs task_id inconsistently (observer.py line 359 vs 287). Could cause privacy leak where unrevealed labels leak to evolver.
6. Observer adds task to _revealed_ids BEFORE checking if reveal condition is met (line 287). Tasks that should remain hidden get marked as revealed.
7. Observer filter_batch_for_evolver() returns original reference for revealed tasks but shallow copy for unrevealed (line 357-366). Asymmetric mutation behavior.

MEDIUM:
8. PolyBench _do_split() sets test=ALL rows instead of proper train/test split.
9. CTF-Dojo Docker failure doesn't set clear error metadata — indistinguishable from agent failure.
10. FutureX builtin_search config may not serialize properly to worker processes.
11. No validation that observer gate is applied before templates receive batch_results.
12. Planner uses instance_id inconsistently across prompt building and assignment filtering.
13. Branch viability check skipped when vc is None.
14. Silent data loss when Activity fails partway through (discovery step masked).

LOW:
15. FutureX answer normalization strips C++ to C.
16. Archive file handle not in context manager.
17. Dead code: ParsePlan action unused.

CANDIDATE ACCEPTANCE CRITERIA:
AC-1: Every finding has file path, line range, affected benchmark(s), severity, evidence, and proposed fix
AC-2: Every finding is verified by static control-flow trace or config trace
AC-3: Review traces all 6 entry scripts through their full execution path
AC-4: Review covers both contributions: navigation branching and multi-agent orchestration
AC-5: Review maps findings to the 3 challenges in challenges.md
AC-6: Findings distinguish confirmed bugs from risks and paper mismatches
AC-7: Cross-benchmark consistency checked for adapter contracts
AC-8: State isolation verified across branches, workspaces, memory, artifacts
AC-9: Final output includes summary table with standardized columns

TASK: Review this candidate plan. Respond in this exact format:
AGREE: points you accept as reasonable
DISAGREE: points you consider unreasonable and why
REQUIRED_CHANGES: must-fix items before the plan is ready
OPTIONAL_IMPROVEMENTS: non-blocking improvements
UNRESOLVED: opposite opinions needing user decisions

## Configuration

- Model: gpt-5.5
- Effort: high
- Timeout: 3600s
- Timestamp: 2026-04-26_00-54-08
