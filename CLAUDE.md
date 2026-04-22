# A-EVOLVE-V2 fork (branch: `a-evolve-1.0-agent-multi`)

This directory is a fork of [A-EVO-Lab/a-evolve](https://github.com/A-EVO-Lab/a-evolve) that ports V2's production benchmarks (ctf_dojo, futurex, polybench), Docker-isolated evolver sandbox, navigation engine, human-in-the-loop, and hypothesis runners onto the official upstream layout. It is the target branch for the `a-evolve-1.0-agent-multi` contribution (multi-agent, harness-modifying).

The fork is **self-contained**: it has its own `.git/`, imports nothing from `../agent_evolve/` or `../backends/`, and can be lifted out of this workspace. The sibling V2 root tree (`/home/ec2-user/A-EVOLVE-V2/`) remains the authoritative production codebase until this fork achieves full parity and is swapped in.

## Layout

```
a-evolve/
├── agent_evolve/                         # matches upstream
│   ├── agents/
│   │   ├── ctf_dojo/, futurex/, polybench/   # NEW (ported from V2 backends/)
│   │   ├── swe/, terminal/, mcp/, mcp_mh/, arc/, skillbench/   # upstream
│   ├── algorithms/
│   │   ├── aevolve/                      # V2 engine (canonical)
│   │   ├── navigation/                   # peer package (NEW)
│   │   ├── skillforge/                   # alias → aevolve + navigation
│   │   ├── mas_adaptive_skill/, meta_harness/, gepa/   # upstream
│   ├── benchmarks/
│   │   ├── ctf_dojo/, futurex/, polybench/   # NEW (ported from V2)
│   │   ├── swe_verified_mini/, mcp_atlas/, skillbench/, skill_bench.py,
│   │   │   tb2/, arc_agi3/, cl_bench.py     # upstream
│   ├── contract/, protocol/, engine/, llm/, tools/, utils/   # V2+upstream merges
├── experiments/                          # ported from V2 wholesale
├── seed_workspaces/                      # symlinks → experiments/<b>/seed
├── examples/                             # symlinks → ../*.sh
├── evaluations/                          # ported from V2 (unchanged)
├── solve_all_with_evolution.py           # ported from V2 (loader updated)
├── ctf_dojo_hypothesis.sh                # ported from V2 (unchanged CLI)
├── futurex_hypothesis.sh                 # ported from V2
├── poly_hypothesis.sh                    # ported from V2
├── sync.sh                               # fork maintenance helpers
├── data → ../data                        # shared dataset (symlink)
└── .upstream-base                        # pinned upstream SHA (pre-UnifiedEngine)
```

## Running experiments

Identical CLI to V2:

```bash
cd a-evolve

bash ctf_dojo_hypothesis.sh H0           # baseline, no evolution
bash ctf_dojo_hypothesis.sh H1           # full evolution
bash ctf_dojo_hypothesis.sh H4           # navigation

bash poly_hypothesis.sh H0
bash futurex_hypothesis.sh H0a            # no-search baseline
bash futurex_hypothesis.sh H0b            # strict search baseline
bash futurex_hypothesis.sh H1             # full evolution + strict search
bash futurex_hypothesis.sh H1b            # full evolution + live search
```

All V2 flags preserved: `--navigation`, `--no-infra-evo`, `--evolver-prompt`, `--branch-confidence`, `--evolver-temp`, `--solver-temp`, `--suffix`, `--verbose`, `--trajectory-only`.

## V2-specific features preserved

| Feature | Location |
|---|---|
| `workspace.protect(['skills','prompts',…])` | `agent_evolve/contract/workspace.py` |
| `infra_dir` (framework-run pipelines w/ network) | `agent_evolve/contract/workspace.py` |
| `BaseAgent.skip_layers` + `tool_registry` | `agent_evolve/protocol/base_agent.py` |
| Docker-isolated `EvolverSandbox` + `HUMAN_TOOL_SPEC` | `agent_evolve/algorithms/aevolve/tools.py` |
| `HumanInterface` (stdin/Telegram/Slack) | `agent_evolve/engine/human_interface.py` |
| Full git branch API | `agent_evolve/engine/versioning.py` |
| `NavigationEngine`, `StrategyTree` | `agent_evolve/algorithms/navigation/` |
| `FailureClassification`, `RoutingEntry`, `BranchInfo` | `agent_evolve/types.py` |
| `EvolveConfig.evolve_infra/tools`, `navigation_enabled`, `branch_confidence_threshold`, `evolver_temperature`, `evolver_include_patches`, `solve_workers` | `agent_evolve/config.py` |
| Trajectory-only observer mode + per-task artifacts | `agent_evolve/engine/observer.py` |

## Upstream relationship

- Remote: `git remote -v` shows `upstream → https://github.com/A-EVO-Lab/a-evolve.git`.
- Anchor: `.upstream-base` pins the SHA we're known-compatible with (pre-UnifiedEngine).
- **Do not run `git rebase upstream/main` automatically.** Minhua Lin's UnifiedEngine refactor deletes `algorithms/{adaptive_skill,adaptive_evolve,guided_synth,skillforge}`, which our `skillforge/` alias currently covers. See Phase 8 below before rebasing.
- Use `./sync.sh fetch-upstream` to pull upstream commits for review (read-only).

## Rebase plan (Phase 8)

After Minhua's UnifiedEngine PR merges upstream and its atom contracts stabilize:

1. `./sync.sh fetch-upstream && git log upstream/main --oneline ^$(cat .upstream-base)` — review changes.
2. `git checkout -b a-evolve-1.0-agent-multi-unified`.
3. `git rebase upstream/main` — our `algorithms/aevolve/`, `algorithms/navigation/`, and `algorithms/skillforge/__init__.py` survive (they live in dirs upstream doesn't touch). Upstream's new `algorithms/unified/` lands cleanly.
4. Port V2's `AEvolveEngine._run_llm` (Docker sandbox) as a UnifiedEngine Operator: `algorithms/unified/recipes/aevolve_docker.py`.
5. Each of ctf_dojo / futurex / polybench declares `FeedbackCapability = pass_fail`; Rule-based Controller routes to the V2 recipe.
6. Re-run baseline diffs against goldens. H0 byte-identical; H1/H4 structurally equivalent.
7. Update `.upstream-base` to post-refactor SHA. Merge.

## Testing

```bash
# Upstream's GEPA test suite (shouldn't regress)
python -m pytest tests/gepa/ -q

# Fork-specific smoke (import paths, harness, protect, branch API)
python -m pytest tests/ -q        # after fork-specific tests are added
```

## Conventions

- Don't modify the V2 root tree (`../agent_evolve/`, `../backends/`, `../experiments/`, `../solve_all_with_evolution.py`, `../*_hypothesis.sh`). Changes there happen independently and flow INTO this fork via `./sync.sh sync-v2`.
- Don't copy dataset files into the fork; `a-evolve/data` is a symlink to `../data`.
- When importing V2 features, always as strict supersets (new kwargs with defaults, new attributes initialised to falsy). Upstream's tests must continue to pass.
