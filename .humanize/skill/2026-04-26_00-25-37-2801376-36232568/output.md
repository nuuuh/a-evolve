This repo is a Python 3.11+ package named `a-evolve`. Its core purpose is evolving agent workspaces against benchmarks through a filesystem contract: prompts, skills, tools, and memory live in directories that evolution algorithms mutate.

**Core Package**
- [agent_evolve/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve) is the main library package.
- [agent_evolve/api.py](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/api.py) exposes the top-level `Evolver` API.
- [agent_evolve/engine/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/engine) contains the generic evolution loop machinery: trial running, observations, history, versioning, and loop control.
- [agent_evolve/contract/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/contract) defines the agent workspace contract: manifests, schemas, and workspace validation.
- [agent_evolve/protocol/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/protocol) defines the base agent interface.
- [agent_evolve/types.py](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/types.py) holds shared task, trajectory, feedback, observation, and result types.

**Algorithms**
- [agent_evolve/algorithms/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/algorithms) contains evolution strategies:
  - `aevolve/`
  - `gepa/`
  - `mas_adaptive_skill/`
  - `meta_harness/`
  - `navigation/`
  - `skillforge/`

**Benchmark And Agent Adapters**
- [agent_evolve/benchmarks/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/benchmarks) contains benchmark adapters for ARC, CTF Dojo, FutureX, MCP Atlas, PolyBench, SkillBench, SWE, Terminal-Bench, and CL Bench.
- [agent_evolve/agents/](/home/ec2-user/A-EVOLVE-V2/a-evolve/agent_evolve/agents) contains benchmark/domain-specific agent implementations, sandboxes, solvers, tools, and dataset helpers.

**Seed Workspaces**
- [seed_workspaces/](/home/ec2-user/A-EVOLVE-V2/a-evolve/seed_workspaces) contains built-in evolvable agent workspaces, each with `manifest.yaml` plus prompts/tools/skills/memory as applicable:
  - `arc/`, `arc-mas/`
  - `mcp/`, `mcp_mh/`
  - `skillbench/`
  - `swe/`
  - `terminal/`

**Examples And Experiments**
- [examples/](/home/ec2-user/A-EVOLVE-V2/a-evolve/examples) has runnable demos and config files for ARC, CL Bench, MCP, SkillBench, SWE, Terminal-Bench, etc.
- [experiments/](/home/ec2-user/A-EVOLVE-V2/a-evolve/experiments) contains more concrete experiment setups, especially for `ctf_dojo`, `futurex`, `futurex_hitl`, `futurex_infra`, `polybench`, and `swe_live`. These include configs, seed workspaces, and evolver prompts.

**Evaluation, Artifacts, Results**
- [evaluations/](/home/ec2-user/A-EVOLVE-V2/a-evolve/evaluations) contains analysis scripts and reports for CTF Dojo, FutureX, and PolyBench.
- [artifacts/](/home/ec2-user/A-EVOLVE-V2/a-evolve/artifacts) stores generated or captured evolved-agent artifacts and reports.
- [results/](/home/ec2-user/A-EVOLVE-V2/a-evolve/results) stores smoke-test/evolution outputs.
- [logs/](/home/ec2-user/A-EVOLVE-V2/a-evolve/logs) appears to be runtime logging output.

**Docs And Paper Material**
- [README.md](/home/ec2-user/A-EVOLVE-V2/a-evolve/README.md) is the main project overview.
- [QUICKSTART.md](/home/ec2-user/A-EVOLVE-V2/a-evolve/QUICKSTART.md), [DESIGN.md](/home/ec2-user/A-EVOLVE-V2/a-evolve/DESIGN.md), and [docs/](/home/ec2-user/A-EVOLVE-V2/a-evolve/docs) provide usage/design docs.
- [paper/](/home/ec2-user/A-EVOLVE-V2/a-evolve/paper) and [figs/](/home/ec2-user/A-EVOLVE-V2/a-evolve/figs) hold paper drafts, reports, diagrams, and figure-generation material.

**Tests And Tooling**
- [tests/](/home/ec2-user/A-EVOLVE-V2/a-evolve/tests) currently focuses on GEPA and SkillBench setup tests.
- [pyproject.toml](/home/ec2-user/A-EVOLVE-V2/a-evolve/pyproject.toml) defines package metadata, optional extras, build config, and Ruff settings.
- [Makefile](/home/ec2-user/A-EVOLVE-V2/a-evolve/Makefile) provides `install`, `test`, `lint`, and `fmt`.
- Root scripts like `*_smoke.sh`, `*_hypothesis.sh`, `solve_all_with_evolution.py`, and `download_futurex_data.py` are convenience runners for benchmark workflows.

In short: `agent_evolve/` is the reusable framework, `seed_workspaces/` are the evolvable agent templates, `examples/` and `experiments/` are runnable workflows, and `evaluations/`, `artifacts/`, `results/`, and `paper/` are analysis/output/research material around those runs.
