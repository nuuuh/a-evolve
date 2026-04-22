# Navigate to Evolve: Decoupling Stationary and Non-Stationary Streams in Agentic Evolution

## 1. The Temporal Setting

The evaluation process for temporal benchmarks is identical to static ones:
tasks arrive in batches, the agent solves them, and the evolver mutates
artifacts between batches. The only difference is that temporal tasks carry
real-world timestamps, which means the task order reflects real-world
chronology and **cannot be shuffled** without destroying the temporal
structure. This single constraint — fixed ordering — introduces distribution
shift that is absent when tasks are i.i.d.

| Property | Static (SWE-verified) | Temporal (PolyBench, CTF-Dojo, FutureX) |
|----------|:---------------------:|:---------------------------------------:|
| Task ordering | Shuffleable (i.i.d.) | Fixed by real-world time |
| Distribution across batches | Approximately constant | Shifts systematically |
| Strategy-relevant properties | Stable (same skills throughout) | Evolve (new primitives, new market regimes, new data sources) |
| Batch score reflects | Agent capability | Agent capability + distribution difficulty (confounded) |
| Experience transfer | Always helps | May help, hurt, or be irrelevant depending on shift |
| Evolution scaling | Monotonic (more cycles → better) | Non-monotonic (early_freeze can outperform full_evo) |


| Benchmark | Domain | Tasks | Span | Baseline | Full Evo | Early Freeze |
|-----------|--------|------:|------|:--------:|:--------:|:------------:|
| **PolyBench** | Prediction markets | 5,075 | 16 days | 68.7% | 80.4% | **81.9%** |
| **CTF-Dojo** | Cybersecurity CTF | 261 | 13 years | 41.8% | 47.9% | **54.8%** |
| **FutureX** | Future event prediction | 332 | 82 days | 47.6% | 45.2% | **46.7%** |

---

## 2. Challenges

What distribution shift introduces:
- C1: Evolution under distribution shift setting
- C2: Learning from Coupled Stationary and Non-stationary Experience
- C3: Evolver Capability Bottleneck


---
### C1: Evolution under distribution shift setting

⚠️ ***Agentic evolution succeeds when past experience transfers to future tasks.***

This assumption holds on static benchmarks where all batches share the same
distribution. On temporal benchmarks, the strategy-relevant properties of
tasks shift over time — not the topic labels, but the techniques required,
environment constraints, information availability, and decision structure.
For entirely new property regions, ***heavily evolved artifacts may not help and
can actively hurt***.

#### Empirical Evidence:
| Benchmark | Full Evo | Early Freeze |
|---|---|---|
| **PolyBench** | 80.4% | **81.9%** |
| **CTF-Dojo** | 47.9% | **54.8%** |
| **FutureX** | 45.2% | **46.7%** |

#### Potential Shifts

**PolyBench** — decision-environment dimensions shift simultaneously, even
within the same topic:

| Property | Early Stream | Late Stream |
|----------|:----------:|:----------:|
| Market certainty (max price >0.95) | 47% | 14% |
| Market uncertainty (0.4–0.6) | 17% | 36% |
| Market liquidity (vol >$1K) | 80% | 14% |

**CTF-Dojo** — challenge environment evolves across 13 years:

| Property | 2011–2014 | 2017–2018 | 2019–2021 | 2022–2024 |
|----------|:---------:|:---------:|:---------:|:---------:|
| Challenge format | 100% text | 100% text | 75% text, 25% script | 75% text, 25% script |
| Files per challenge | 1 | 1 | 1–2 | 2–3 |
| Runtime dependency | 62% text | 66% glibc | 50% text, 30% binary | 55% text, 15% Python |

**FutureX** — information access requirements shift:

| Property | Early (batch 1–5, n=100) | Late (batch 12–17, n=112) |
|----------|:------------------------:|:-------------------------:|
| Chinese-language tasks | 1% | 25% |
| Unsearchable platform data | 3% | 45% |
| Level 3–4 difficulty | 10% | 47% |
| Accuracy (baseline) | 49% | 30% |

### C2: Learning from Coupled Stationary and Non-stationary Experience

⚠️ ***Distribution shift is not all-or-nothing — part of accumulated experience
transfers and part does not.***

Evidence: fully evolved agent still beats baseline agent

The system must determine **which knowledge to
use** per task, not load everything. The current single-path evolver cannot
decompose this: one workspace applies all mutations globally.

```
 Accumulated Experience (single-path: loads ALL for EVERY task)
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  🟢 Stationary (reuse always)       🔴 Non-stationary (local only)  ║
║  ┌─────────────────────────────┐    ┌────────────────────────────┐  ║
║  │ Flag verification tool      │    │ Classical crypto skills    │  ║
║  │ Illiquidity detection       │    │ Memorized Oscar results    │  ║
║  │ Temporal disambiguation     │    │ "Follow consensus" rule    │  ║
║  │ Data API access patterns    │    │ "Recall known flags" rule  │  ║
║  │                             │    │                            │  ║
║  │ 🟢 Helps ALL tasks          │    │ 🔴 Helps ONLY originating  │  ║
║  │ 🟢 Should persist forever   │    │    window's tasks          │  ║
║  │ ⚠️  Under-invested          │    │ 🔴 Pollutes other tasks    │  ║
║  └─────────────────────────────┘    └────────────────────────────┘  ║
║                                                                      ║
║  ⚠️  Evolver CANNOT separate → loads 🟢 + 🔴 for every task         ║
╚══════════════════════════════════════════════════════════════════════╝
```


### C3: Evolver Capability Bottleneck

⚠️ ***C1 and C2 show that evolution quality degrades under distribution shift. C3 identifies two obstacles to fixing this: the evolver system is too weak, and evolution driven purely by historical experience struggles under severe shift.***

```
Evolver capability ──────────────────────────────────────────────────▶

Weak Evolver          Strong Evolver          Stronger + HITL
    │                      │                        │
    │  prompt tweaks       │  + individual tools    │  + infra pipelines
    │  memory edits        │  + API wrappers        │  + wrapped strategies
    │                      │  (solver must select   │  + business logic
    │                      │   & orchestrate each)  │  (solver invokes
    │                      │                        │   implicitly)
    ▼                      ▼                        ▼
 ───┤──────────────────────┤────────────────────────┤──────
  artifacts              tools                  infrastructure
  (easy, limited)        (explicit, verbose)    (implicit, effective)
```

Why we need stronger and robust evolution:

**1. Domains require heavy evolution from scratch.**
- Some domains start with near-zero infrastructure (no tools, no APIs, no pipelines)
- Evolver must build everything from historical experience signals: diagnose → find APIs → write tools → debug → integrate
- Demands sustained multi-step reasoning across cycles, far beyond prompt/skills/memories tweak

**2. Towards infrastructure-level evolution.**
- Difference against tools: solver must discover, select, orchestrate each one at inference time (costs tokens + steps)
- Infrastructure pipelines: domain logic pre-compiled (sourcing → validation → formatting), solver invokes implicitly
- Building pipelines requires stronger evolution systems (multi-agent, task boards, structured planning)

**3. Human provision under severe distribution shift.**
- Current evolution is purely ***experience-driven*** (past failures → mutations)
- Under severe shift, historical experience becomes misleading or insufficient
- Human-in-the-loop (HITL) during evolution provides what experience cannot: credentials, domain judgment, proactive direction

---

## 3. Solution: Decoupled Evolution with Agentic Navigation

*Full formal framework, pseudocode, and theoretical analysis: [solution_detailed.md](solution_detailed.md)*

**Core idea:** Decouple evolution into two streams — stationary (on trunk)
and non-stationary (on branches) — with per-task agentic navigation.

***Key difference from current A-evolve:*** 
  - F_evaluate
  - F_branch
  - F_navigate
  - Decouple tools and pipeline/infrastructure
---


```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   A-Evolve (current)              Decoupled (proposed)              │
│                                                                     │
│   π_S → Δ₁ → Δ₂ → Δ₃ → ...      main (root): 🟢 stationary       │
│   ┌──────────────────────┐         │  commit: flag verification    │
│   │ Single linear chain  │         │  commit: illiquidity detect   │
│   │ ALL artifacts for    │         │                               │
│   │ ALL tasks            │         ├── branch/A: 🔴 non-stationary │
│   │                      │         │   RSA/ECC tools               │
│   │ ⚠️  Cannot separate   │         ├── branch/B: 🔴 non-stationary │
│   │ stationary from      │         │   skip-illiquid rule          │
│   │ non-stationary       │         └── branch/C: 🔴 non-stationary │
│   └──────────────────────┘             platform-data strategy      │
│                                                                     │
│   Every task gets everything       Each task gets main + 1 branch   │
└─────────────────────────────────────────────────────────────────────┘
```

### Solve: Per-Task Navigation

```
┌────────────────────┐      ┌──────────────────────────┐
│  Task xᵢ arrives   │─────▶│  F_NAVIGATE(xᵢ, Tree)    │
└────────────────────┘      │                          │
                            │  Read task description   │
                            │  Select leaf node        │
                            └────────────┬─────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
     ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
     │  main (root)   │        │  branch/A      │        │  branch/B      │
     │                │        │                │        │                │
     │ 🟢 stationary  │        │ 🟢 main (inherited) │   │ 🟢 main (inherited) │
     │    artifacts   │        │ + 🔴 RSA tools  │        │ + 🔴 skip rule  │
     └───────┬────────┘        └───────┬────────┘        └───────┬────────┘
             │                         │                         │
             ▼                         ▼                         ▼
        git checkout              git checkout              git checkout
        load workspace            load workspace            load workspace
             │                         │                         │
             ▼                         ▼                         ▼
        AGENT.solve               AGENT.solve               AGENT.solve
```

### Evolve: Adaptive Tree Evolution

```
  batch results B = [(x, τ, f, leaf), ...]
                    │
                    ▼
  ┌─────────────────────────────────────────────────┐
  │  F_EVALUATE → behavioral diagnostics            │
  │  Classify each failure:                         │
  │    recurrent across branches? → 🟢 stationary   │
  │    approach mismatch?         → 🔴 non-stat.    │
  └──────────┬──────────────────────┬───────────────┘
             │                      │
    🟢 stationary              🔴 non-stationary
             │                      │
             ▼                      ▼
  ┌──────────────────┐   ┌──────────────────────┐
  │  DEEPEN main     │   │  BRANCH              │
  │  git commit      │   │  git checkout -b     │
  │  git rebase all  │   │  git commit          │
  │  → propagates    │   │  → isolated          │
  └────────┬─────────┘   └──────────┬───────────┘
           │                        │
           └────────────┬───────────┘
                        │
           ┌────────────▼────────────┐
           │  PROMOTE / LIFECYCLE    │
           │  generalize? → merge   │
           │  stale? → delete       │
           ├────────────────────────┤
           │  EVOLVE NAVIGATOR      │
           │  routing outcomes →    │
           │  navigation tools      │
           │  on main               │
           └────────────┬───────────┘
                        ▼
                 Updated Tree T
```

### Git Tree Over Time

```
Batch 1-5 (no shift → single-path = A-Evolve):

  main:  ○──○──○──○──○

Batch 6 (shift detected → branch):

  main:  ○──○──○──○──○──○
                          ╲
         branch/A:         ○──○

Batch 7+ (both streams evolve):

  main:  ○──○──○──○──○──○──○──○
                          ╲
         branch/A:         ○──○──○──○
                                ╲
         branch/B:               ○──○

Promotion (branch/A generalizes → merged):

  main:  ○──○──○──○──○──○──○──○──●
                                ╲
         branch/B:               ○──○  (rebased)
```


Infra vs tools: implicitly or explicitly used by the solver agent

```
results/experiment/
├── solver_workspace/              ← what the agent uses to solve tasks
│   ├── prompts/system.md
│   ├── skills/*/SKILL.md
│   ├── memory/*.jsonl
│   ├── tools/*.py                 ← sandbox tools (--network none)
│   ├── 🟢 infra/                     ← NEW: infrastructure (framework-executed, has network)
│   │   ├── search_pipeline.py     ← evolvable search strategy
│   │   ├── sandbox_setup.sh       ← evolvable Docker tool installation
│   │   └── submit_handler.py      ← evolvable submission format
│   └── .git/                      ← strategy tree (main + branches)
│
└── evolver_workspace/             ← meta-strategy (evaluation + navigation)
    ├── evaluator.py               ← F_Evaluate: classify failures
    ├── navigator.py               ← F_Navigate: route tasks to branches
    ├── branch_policy.py           ← branching/promotion/pruning decisions
    ├── routing_log.jsonl          ← accumulated routing outcomes
    └── .git/                      ← evolver's own versioning
