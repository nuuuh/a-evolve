CORE_RISKS:
- “Implementation is correct” is too broad. Without explicit expected behavior per benchmark and contribution, reviewers may produce subjective findings or miss paper-critical defects.
- Benchmark-only scope may still require reviewing shared infrastructure: config loading, evolution loop, observer, git branch handling, tool/workspace mutation, scoring, and runner orchestration.
- Entry scripts may not cover real experiment paths. Smoke and hypothesis scripts can pass while full benchmark orchestration, branch selection, or multi-agent evolution is broken.
- Paper docs may describe intended behavior, not implemented behavior. Treating them as ground truth without checking experiment configs and runtime flow could create false positives.
- “Verify identified bugs” needs a standard. Some bugs require reproductions, some require static reasoning, and some may depend on unavailable benchmark data or external services.
- Navigation and orchestration are high-risk because they involve stateful git operations, branch isolation, score attribution, agent handoffs, and cross-cycle workspace mutation.
- Distribution shift and coupled experience are conceptual challenges; the plan does not define what concrete implementation behaviors should mitigate them.

MISSING_REQUIREMENTS:
- Define review boundaries for shared modules used by the benchmarks, especially `agent_evolve/config.py`, `agent_evolve/types.py`, `agent_evolve/engine/loop.py`, and `solve_all_with_evolution.py`.
- Include config coverage: YAML defaults, benchmark-specific overrides, missing fields, path resolution, seed handling, budget limits, and algorithm selection.
- Check whether entry scripts invoke the intended configs, algorithms, agents, and benchmarks.
- Review score normalization and comparison across branches/tasks, especially for navigation.
- Verify that failed, timed-out, or partially completed runs do not corrupt evolution state.
- Check git safety: branch creation, checkout behavior, dirty worktree handling, conflict handling, cleanup, and whether benchmark artifacts leak across branches.
- Check reproducibility: random seeds, deterministic benchmark subsets, logging, output directories, and resume behavior.
- Include privacy/safety behavior in `observer.py`, since evolved workspaces may capture sensitive task data.
- Review benchmark adapters for contract consistency: input format, timeout handling, scoring direction, success criteria, artifacts, and exception behavior.
- Include negative cases: missing tools, invalid benchmark path, empty task set, no successful branch, no improvement, invalid evolved files.
- Require distinguishing “paper mismatch,” “runtime bug,” “experimental validity risk,” and “code hygiene issue.”

TECHNICAL_GAPS:
- The plan lists files but not review method. It should specify static trace, script/config audit, and minimal execution checks separately.
- It does not define how to verify multi-agent orchestration without invoking costly or nondeterministic model calls.
- It does not say whether reviewers may run scripts. “Do not modify anything” still allows read-only commands, but benchmark scripts may write outputs or mutate git branches.
- There is no explicit baseline for expected behavior from `paper/navigation_implementation.md` and `paper/multi_agent_orchestration.md`.
- The plan does not identify critical interfaces between modules: engine loop to algorithm engine, algorithm engine to benchmark adapter, benchmark score to navigator, analyst to evolver.
- It omits artifact inspection: logs, result schemas, branch metadata, evolution histories, and saved observations may reveal bugs not visible in source.
- It does not constrain severity levels, which makes the final summary table harder to use.

ALTERNATIVE_DIRECTIONS:
- Paper-claim-driven review: start from each contribution/challenge claim, trace required implementation paths, then verify benchmark coverage. Best for publication risk, but may miss ordinary runtime bugs.
- Entry-script-driven review: trace each of the six scripts through configs, runner, algorithm, benchmark, and outputs. Best for experiment reproducibility, but less complete for unused code paths.
- Interface-contract review: define contracts for benchmark adapters, engines, observer, navigation, and orchestration, then check each implementation. Best for architecture correctness, but requires more upfront structure.
- Failure-mode review: focus on branch contamination, score misattribution, invalid evolved workspaces, timeout handling, and resume/cleanup behavior. Best for finding serious bugs, but less comprehensive.
- Minimal dry-run review: run only safe read-only/static commands plus mocked or tiny benchmark invocations. Best for verification, but requires clear permission because scripts may write files or mutate git state.

QUESTIONS_FOR_USER:
- Should the reviewer run any commands, or is this strictly static review?
- If commands are allowed, may they run scripts that create output files, checkout branches, or invoke models?
- Are paper docs authoritative, or should implementation/configs be treated as the source of truth when they disagree?
- Should findings include paper-alignment issues, or only executable code bugs?
- What severity scale should be used?
- Are external services, API keys, benchmark datasets, or Docker environments expected to be available?
- Should proposed fixes be high-level, or should the reviewer identify exact files/functions to change?

CANDIDATE_CRITERIA:
- Every finding must include file path, function/script/config location, affected benchmark(s), severity, evidence, and proposed fix.
- Every finding must be verified either by reproduction, static control-flow trace, config trace, or a clearly stated invariant violation.
- Review must trace all six entry scripts to the selected benchmark, agent, config, algorithm, output path, and scoring path.
- Review must explicitly cover the two contributions: navigation branch isolation/routing and analyst+evolver orchestration.
- Review must explicitly map implementation behavior to the three challenges in `paper/challenges.md`.
- Review must distinguish confirmed bugs from risks, paper mismatches, and open questions.
- Review must check cross-benchmark consistency for PolyBench, CTF-Dojo, and FutureX adapter contracts.
- Review must check state isolation: branches, workspaces, memory, generated artifacts, benchmark outputs, and observations.
- Final output should include a summary table with: ID, severity, benchmark, component, finding, evidence, impact, proposed fix, verification method.
