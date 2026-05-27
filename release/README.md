# Adaptive Auto-Harness

Code accompanying the paper **"Adaptive Auto-Harness: Stateful
Multi-Agent Evolution and Solve-Time Routing for LLM Agents on
Open-Ended Task Streams"** (anonymous submission).

The framework constructs and adapts an agent's *harness* — its
prompts, skills, tools, and supporting infrastructure — for
open-ended task streams. It contains:

- A multi-agent evolver that decomposes evolution into Analyst,
  Researchers, Builder, and Verifier with persistent cross-cycle
  memory and a temporal-reveal feedback gate.
- A solve-time router that selects a specialized harness branch per
  task from an evolved harness tree.
- Two human-steering hooks for cases when stream history lacks the
  signal needed to build the next harness.
- Three benchmark adapters: PolyBench (prediction markets),
  CTF-Dojo (security challenges), FutureX (event forecasting).

## Layout

```
.
├── agent_evolve/         # core library (algorithms, agents, tools)
├── experiments/          # per-benchmark configs, prompts, seeds
│   ├── ctf_dojo/
│   ├── futurex/
│   └── polybench/
├── seed_workspaces/      # initial workspaces consumed by each benchmark
├── scripts/              # hypothesis runners (one per benchmark + baselines)
├── data/                 # see data/README.md to populate datasets
├── tests/                # pytest suite
├── solve_all_with_evolution.py
├── pyproject.toml
└── .env.template
```

## Quick start (PolyBench)

The instructions below walk through a PolyBench run end to end.
CTF-Dojo and FutureX follow the same shape with their own runner
scripts; see *Other benchmarks* below.

After unpacking the supplement archive and entering the resulting
directory:

```bash
# 1. Install (the [all] extra pulls every supported provider and backend)
pip install -e ".[all]"

# 2. Configure secrets and model IDs
cp .env.template .env
# Edit .env to set SOLVER_MODEL, EVOLVER_MODEL, and provider credentials.

# 3. Download PolyBench data (see data/README.md for the source URL
#    and required schema)
python data/download_data.py --benchmark polybench

# 4. Run the no-evolution baseline on PolyBench
bash scripts/poly_hypothesis.sh H0
```

PolyBench targets:

| Target | Configuration                                  |
|--------|------------------------------------------------|
| `H0`   | No-evolution baseline                          |
| `H1`   | Full evolution (multi-agent)                   |
| `H4`   | Navigation only (solve-time routing)           |
| `H5`   | Full system (multi-agent evolution + routing)  |

Results are written to `results/polybench_<config>/results.jsonl`
with per-task trajectories alongside.

See `INSTALL.md` for the full list of environment variables, supported
LLM providers, and minimal-install options.

## Other benchmarks

The supplement also includes runnable adapters for the other two
benchmarks reported in the paper. The flow mirrors PolyBench: download
the data, then run the hypothesis script. Refer to `data/README.md`
for source links and to each script's header for available targets.

| Benchmark | Script                            |
|-----------|-----------------------------------|
| CTF-Dojo  | `scripts/ctf_dojo_hypothesis.sh`  |
| FutureX   | `scripts/futurex_hypothesis.sh`   |
| Baselines | `scripts/baselines_hypothesis.sh` |

## License

MIT.
