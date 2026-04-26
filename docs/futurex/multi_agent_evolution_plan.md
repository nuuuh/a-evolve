# Multi-Agent Evolution: Template Design Plan

## Goals

1. **Beat naive single-agent evolution on final accuracy.** The current
   H1 single-agent achieves 42.9% on the FutureX 56-task smoke test.
   At least one multi-agent template must match or exceed this.

2. **Verify evolution produces functional web-search tools.** The
   evolver must build working API wrappers and search pipelines —
   not broken stubs or DEPRECATED placeholders. Evidence: evolved
   `tools/registry.yaml` contains tools that return real data when
   tested in the solver sandbox (network success rate > 80%).

3. **Verify the solver actively uses evolved search to improve
   predictions.** The solver must call evolved tools via bash to
   gather external evidence, and that evidence must demonstrably
   change its answers compared to pure-LLM reasoning. Evidence:
   batch 2+ pass rate > batch 1 (pre-evolution) pass rate, with
   `bash` tool_use counts >> 0 in post-evolution trajectories.

## Why single-agent evolution beats multi-agent (and how to fix it)

On FutureX, H1 (single-agent) achieves 42.9% vs H1_multi (orchestrated
multi-agent) at 35.7%. The single evolver succeeds because it
accumulates **sandbox context** across dozens of tool calls within one
long session — it discovers APIs, tests them, builds tools, fixes
errors, all with continuous feedback. The orchestrated template
fragments this into short, isolated LLM calls guided by a planner
that has no deep insight into what works at the bash level.

This is a C3 problem (evolver capability bottleneck): the multi-agent
system is structurally weaker than the single agent because it trades
depth for breadth without compensating for the lost iteration.

## Design principles

Five principles drawn from MLEvolve (MCGS-based ML solution search)
and our empirical evidence:

**P1. The workspace IS the protocol.** Agents should communicate
through workspace state (files, git branches, tool registries), not
through conversational handoffs. MLEvolve's search tree is the
communication medium — agents read nodes and write new nodes. In our
system, the git workspace plays this role.

**P2. State-based dispatch over conversational routing.** Route to
mutation operators by inspecting artifact state (do tools exist? do
they pass tests? is the score stagnant?) rather than asking an LLM
planner to decide. MLEvolve dispatches to `debug_agent` when code
has errors, `evolution_agent` when stagnant — simple conditionals,
not an LLM "manager."

**P3. Pre-commit validation.** MLEvolve's `code_review_agent`
validates code before execution. Our H1_multi evolver wrote tools with
53% runtime failure rate — a cheap review/test step between "write"
and "deploy" would catch this.

**P4. Tiered escalation under stagnation.** MLEvolve escalates from
parameter tweaks → component changes → paradigm shifts when patience
counters detect plateau. This prevents the LLM from proposing minor
variations of the same broken approach.

**P5. Fusion over selection.** MLEvolve's `fusion_agent` merges
insights from multiple branches by analyzing *why* they work, not
just picking the highest-scoring one. Selection discards partial
successes; fusion composes them.

## Template design space

Each template represents a point in a design space with three axes:

```
Axis 1: Iteration depth
  shallow (1 pass) ────────────── deep (build-test-fix loop)

Axis 2: Agent diversity
  homogeneous (N identical) ──── heterogeneous (specialized roles)

Axis 3: Selection pressure
  none (commit everything) ────── competitive (keep only best)
```

The five candidates span this space:

| Template | Depth | Diversity | Selection | Paper alignment |
|---|---|---|---|---|
| A: verified | Deep (retry loop) | Low (evolver + verifier) | Quality gate | C3: stronger evolver via iteration |
| B: specialists | Shallow (1 pass) | High (role-per-layer) | Merge all | C2: decompose coupled experience by layer |
| C: debate | Medium (2 passes) | Medium (proposer + critic) | Critique filter | C3: adversarial quality assurance |
| D: mosaic | Deep (N passes) | High (per-branch evolvers) | Fusion | C1+C2: per-branch specialists + fusion |
| E: adaptive | Varies (state-driven) | Varies (dispatch) | Escalation | C3+MCTS: tree search with backprop |

## Candidate A: `verified` — build-verify-retry

**Thesis:** The single-agent advantage is the build-test-fix loop.
Restore it in multi-agent form with an explicit verification step.

```
Planner → diagnosis
  │
  └─ per assignment:
       Evolver ──build──▶ Verifier ──test──▶ pass? → commit
                                              │
                                            fail? → Evolver (retry with feedback)
                                              │       (max 2 retries)
```

**Agents:** 1 planner + 1 evolver + 1 verifier per assignment.
Verifier has sandbox+bash — runs each tool against sample queries.

**Theory:** Approximates the single-agent's tight feedback loop
without requiring one long session. The verifier provides the "did
my tool actually work?" signal that fragmented calls lose.

**Aligns with:** C3 (stronger evolver through iteration), P3
(pre-commit validation from MLEvolve).

---

## Candidate B: `specialists` — parallel layer experts

**Thesis:** Evolution failure is partly a context-window problem —
one evolver must simultaneously reason about tools, prompts, skills,
and memory. Splitting by workspace layer lets each agent focus.

```
Planner → shared diagnosis
  │
  ├─ Tool Builder (tools/*.py only)        ┐
  │    sandbox + network, API testing       │ parallel
  │                                         │
  └─ Strategy Writer (prompts/ + skills/)  ┘
       reads tool registry, writes strategy

  ──── barrier ────

  Git merge tool-branch + strategy-branch → main
```

**Agents:** 1 planner + 2 specialists (tool builder, strategy writer)
running concurrently on separate git branches. Non-overlapping file
sets → merge is conflict-free.

**Theory:** Decomposition by workspace layer mirrors C2's insight
that experience decomposes into stationary (tools, infra) and
non-stationary (prompts, skills) components. Tool building is
stationary (APIs don't change); strategy writing is non-stationary
(adapts to task distribution).

**Aligns with:** C2 (decompose coupled experience), P1 (workspace
as protocol — specialists communicate via the merged workspace, not
via conversation).

---

## Candidate C: `debate` — propose-critique-revise

**Thesis:** Tool quality degrades in multi-agent because no one
reviews the code. An adversarial critic catches errors the proposer
misses, without needing a full sandbox test.

```
Planner → diagnosis
  │
  └─ per assignment:
       Proposer ──write──▶ Critic ──review diff──▶ accept? → commit
          │                                          │
          └──────── revise (with critique) ◀─────── reject
```

**Agents:** 1 planner + 1 proposer (full sandbox) + 1 critic (no
sandbox, reads diff only — cheap LLM call).

**Theory:** Adversarial review improves code quality at low cost.
The critic is a "fast verifier" — it catches structural issues
(missing error handling, wrong import, inconsistent registry) from
the diff alone, without executing code. Cheaper than running tools.

**Aligns with:** C3 (quality assurance), P3 (pre-commit review
from MLEvolve's code_review_agent).

---

## Candidate D: `mosaic` — per-branch specialists with fusion

**Thesis:** Navigation creates branches for non-stationary regimes
(C1). But the current system evolves all branches with the same
generic evolver. Each branch should have a specialist evolver, and
a fusion agent should cross-pollinate successful techniques.

```
Planner → diagnosis + branch allocation
  │
  ├─ Evolver-main (stationary improvements)      ┐
  ├─ Evolver-branch/A (regime-A specialist)       │ parallel
  ├─ Evolver-branch/B (regime-B specialist)       │
  └─ ...                                          ┘

  ──── barrier ────

  Fusion Agent: read all diffs, identify transferable
    techniques, merge selectively into main
```

**Agents:** 1 planner + N branch evolvers (parallel) + 1 fusion
agent. Each branch evolver gets only its branch's tasks and a
focused prompt. The fusion agent analyzes *why* each branch's
changes work and selectively incorporates generalizable techniques
into main.

**Theory:** Directly implements the navigation paper's vision: main
holds stationary knowledge, branches hold non-stationary adaptations,
and cross-branch transfer happens through principled fusion rather
than blind merging. This is MLEvolve's fusion_agent (P5) applied to
the strategy tree.

**Aligns with:** C1+C2 (per-branch specialization + selective
transfer), P5 (fusion over selection from MLEvolve).

---

## Candidate E: `adaptive` — state-driven dispatch with escalation

**Thesis:** The right evolution strategy depends on the current
state of the workspace. A fresh workspace needs tool building; a
workspace with broken tools needs debugging; a workspace with
working tools but stagnant scores needs strategy rethinking.
Hard-coding one pipeline is wrong.

```
State inspection:
  │
  ├─ no tools exist          → dispatch: ToolBuilder (build from scratch)
  ├─ tools exist, >30% error → dispatch: Debugger (fix broken tools)
  ├─ tools work, score=prev  → dispatch: Strategist (rethink approach)
  │                             (escalation: tweak → restructure → paradigm shift)
  └─ tools work, score up    → dispatch: Refiner (small improvements)

Each dispatch = one _run_llm call with a role-specific prompt.
Score comparison = current batch vs previous batch.
```

**Agents:** No fixed agent count. 1-4 agents per cycle depending on
workspace state. State inspection is deterministic (file checks, not
LLM). Each dispatched agent gets a role-specific prompt.

**Theory:** Inspired by MLEvolve's MCGS node-selection: the mutation
operator is chosen by the node's state, not by an LLM planner (P2).
Patience counters track consecutive non-improving cycles and trigger
escalation (P4): after 2 flat cycles, the strategist prompt changes
from "tweak" → "restructure" → "try a completely different approach."

The key difference from orchestrated: **no LLM planner**. The planner
is replaced by deterministic state inspection + dispatch rules. This
eliminates the shallow-diagnosis problem entirely.

**Aligns with:** C3 (escalation against capability bottleneck), P2
(state-based dispatch), P4 (tiered escalation from MLEvolve's MCGS).

---

## Comparison matrix

| | A: verified | B: specialists | C: debate | D: mosaic | E: adaptive |
|---|---|---|---|---|---|
| Agents/cycle | 2-4 | 3 | 3 | N+2 | 1-4 (varies) |
| Parallelism | Sequential | Full | Sequential | Full | Sequential |
| LLM planner? | Yes | Yes | Yes | Yes | **No** (deterministic) |
| Iteration | Yes (retry) | No | Yes (revise) | No | Yes (escalation) |
| Addresses C1 | No | No | No | **Yes** (per-branch) | Partially |
| Addresses C2 | No | **Yes** (layer decomp) | No | **Yes** (fusion) | Partially |
| Addresses C3 | **Yes** (verification) | Partially | **Yes** (critique) | Partially | **Yes** (escalation) |
| MLEvolve principle | P3 | P1 | P3 | P5 | P2, P4 |
| Implementation | ~200 LOC | ~250 LOC | ~200 LOC | ~300 LOC | ~250 LOC |
| Cost vs orchestrated | 1.5-2x | 1.5x | 1.5x | Nx | 1-2x |

## Experiment plan

### Configs

Each template is activated via a single YAML key:

```yaml
orchestrator: verified              # → templates/verified.py
orchestrator: debate                # → templates/debate.py
orchestrator: parallel_specialists  # → templates/parallel_specialists.py
orchestrator: mosaic                # → templates/mosaic.py
orchestrator: adaptive              # → templates/adaptive.py
```

Config files live at `experiments/futurex/configs/<name>_evo.yaml`,
identical to `full_evo_multi.yaml` except the `orchestrator:` key.

### Run commands

```bash
COMMON="python solve_all_with_evolution.py
  --benchmark futurex
  --seed-workspace experiments/futurex/seed
  --evolver-prompt experiments/futurex/evolver_prompt.md
  --temporal-reveal
  --task-timeout 300
  --workers 10
  --max-turns 80
  --stride 6
  --batch-size 10
  --evolver-temp 0
  --solver-temp 0
  --no-infra-evo"

# Run all five in parallel (each uses its own output dir + sandboxes)
for tmpl in verified debate parallel_specialists mosaic adaptive; do
  $COMMON \
    --output-dir results/futurex_smoke_${tmpl}_evo \
    --config experiments/futurex/configs/${tmpl}_evo.yaml \
    > logs/futurex_${tmpl}_evo.log 2>&1 &
  echo "Started $tmpl (PID $!)"
done
```

### Monitoring

```bash
# Progress
for d in results/futurex_smoke_*_evo; do
  n=$(wc -l < "$d/results.jsonl" 2>/dev/null || echo 0)
  echo "$(basename $d): $n/56"
done

# Pass rate
python3 -c "
import json, glob
for d in sorted(glob.glob('results/futurex_smoke_*_evo')):
    rows = [json.loads(l) for l in open(f'{d}/results.jsonl') if l.strip()]
    p = sum(r.get('success',False) for r in rows)
    print(f'{d.split(\"/\")[-1]:40s} {p}/{len(rows)} = {100*p/len(rows):.1f}%')
"
```

### Expected comparison table

| Experiment | Template | Compare against | Key question |
|---|---|---|---|
| H1_smoke | (single-agent) | H0b baseline | Does evolution help? |
| H1_multi_smoke | orchestrated | H1 | Does multi-agent help? (currently: no) |
| H1v_smoke | verified | H1_multi | Does verification fix tool quality? |
| H1d_smoke | debate | H1_multi | Does adversarial review fix tool quality? |
| H1s_smoke | specialists | H1_multi | Does layer decomposition help? |
| H1m_smoke | mosaic | H1_multi | Does per-branch specialization + fusion help? |
| H1a_smoke | adaptive | H1_multi | Does state-driven dispatch beat LLM planning? |

**Target:** at least one multi-agent template matches or beats H1's
42.9% on the overlapping 56-task sample.

### Key metrics

1. **Pass rate** — primary metric, compare with H1 (42.9%) and
   H1_multi (35.7%)
2. **Network success rate** — tool reliability (H1=84%, H1_multi=47%)
3. **Evolved tool diversity** — how many functional tools created
4. **Agents spawned per cycle** — measure actual multi-agent activity
5. **Batch 2 pass rate** — early evolution effectiveness (H1=60%)
