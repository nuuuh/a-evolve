# Structured Evolution: Process-Driven Multi-Agent Template

## Goals

1. **Exceed single-agent evolution pass rate on FutureX smoke test.**
   H1 single-agent scores 36.9% on the current 84-task dataset (503
   tasks, stride 6). The structured evolution template must beat this
   through better infrastructure building, not just more agents.

2. **Solver uses ≥13 bash calls/task on average.** V1/V2 showed that
   multi-agent evolvers throttle the solver's search budget. The
   evolved system prompt must not cap search count.

3. **Evolved infra pipelines produce sophisticated, generalizable
   web search capability.** V1/V2 evolvers produce shallow tool
   scripts that hardcode a single URL. Real web search is a
   multi-stage problem: query formulation, search engine selection,
   content retrieval, content extraction and reformulation into
   agent-friendly text, rate limiting, and fallback handling. The
   structured template must evolve `infra/` pipelines that tackle
   these stages end-to-end — generalizable search infrastructure,
   not one-off scripts for specific data sources.

4. **Network success rate > 80%.** Evolved tools must return real
   data in the solver sandbox, validated with strict criteria.

## Acceptance criteria

- **AC1**: `structured_evolution.py` template implemented, imports
  cleanly, passes 4-task pipeline test showing all 4 phases
  (analyze → research → build → verify) in trajectory.
- **AC2**: `_evolution_workspace.py` helpers implemented with tests:
  `load_task_board`, `update_task_board`, `load_research_log`,
  `append_research`, `validate_research_record`.
- **AC3**: Build-verify loop tested: builder writes a broken tool →
  verifier rejects → builder retries with feedback → verifier
  accepts. Max 3 retries. Test proves the loop fires.
- **AC4**: HITL integration points work: research agent can request
  credentials via `human_interface`, task board accepts human
  entries. Test with mock HITL interface.
- **AC5**: Pass rate measured on 84-task FutureX smoke. Template
  must exceed H1's 36.9% on the same task set.
- **AC6**: Evolved workspace contains `task_board.md` with failure
  patterns, `research_log.jsonl` with ≥5 verified records, and
  `architecture.md` documenting what was built.
- **AC7**: Full test suite passes (280+ tests, 0 failures).

## Why V1/V2 failed — root causes

### R1. Context fragmentation (V1)
Multi-agent splits the discover → build → test → fix loop across
isolated LLM calls, losing the causal chain.

### R2. Planner adds no signal (V1/V2)
The planner sees task IDs and scores but not task text or tool
outputs. It produces generic guidance ("improve search strategy").

### R3. Solver search throttling (V1/V2)
Multi-agent evolvers write "use 2-4 searches" into the system
prompt. H1's solver averages 13.3 bash calls/task.

### R4. All evolvers converge on the same narrow approaches (V2)
Every V2 template converges on the same small set of tools/methods.
None discovered alternative approaches that could cover more task
subtypes. The evolver can't discover approaches it doesn't know
exist — and one-shot LLM calls don't have enough turns for
systematic exploration within a capability regime.

### R5. No knowledge accumulation across cycles (V1/V2)
Each evolution cycle starts fresh. Cycle 3's evolver doesn't know
that cycle 1 already tested DuckDuckGo and found it times out.
The discovery_cache (V2-H) attempted this but the cache was
too shallow — just file existence, not structured research records.

### R6. No separation of research from building (all)
The single-agent and all multi-agent templates mix unverified
experiments with production builds. The evolver discovers an
approach, gets output back, and immediately writes a tool —
without checking if the output is correct, if the approach is
reliable, or if it handles edge cases.

## Design: 4-phase structured evolution

### Overview

```
SOLVER WORKSPACE (results/<run>/futurex/)
  prompts/system.md   — solver prompt
  tools/              — independent tool scripts
  infra/              — pipeline ecosystem (built by evolver)
  skills/             — reasoning heuristics

EVOLVER WORKSPACE (results/<run>/evolver_workspace/)  ← sibling, NOT inside solver
  task_board.md       — failure patterns + prioritized gaps
  research_log.jsonl  — {approach, tested, works, evidence}
  architecture.md     — what was built and why
  insights.jsonl      — cross-cycle lessons
  evolution/          — evolver conversation trajectories

Docker mounts:
  /solver_workspace   — RW (evolver writes tools/infra/prompts here)
  /evolver_workspace  — RW (evolver reads/writes state here)
  /trajectories       — RO (safe solver trajectories for analysis)

Solver sees ONLY /solver_workspace. Evolver sees both.

Phase 1: ANALYZE → Phase 2: RESEARCH → Phase 3: BUILD → Phase 4: VERIFY
                                                    ↑               │
                                                    └── retry ──────┘
```

### Phase 1: Analyze (1 agent, read-only)

**Agent:** Analyst (CallLLMSimple — no sandbox, no network)

**Reads:**
- Solver batch trajectories (via `build_evolution_prompt`)
- `evolver_workspace/task_board.md` (prior cycle's analysis)
- `evolver_workspace/research_log.jsonl` (what's been tried)

**Writes:**
- Updated `evolver_workspace/task_board.md` with:
  - New failure patterns from this batch
  - Prioritized gap list (what to research next)
  - Regime categories discovered from task text

**Why separate agent:** The analyst reads ALL trajectories
holistically and produces structured output. The single-agent
evolver spends its context on one trajectory at a time and
jumps to building before finishing analysis.

**Output format** (task_board.md):
```markdown
## Failure Patterns (Cycle N)
- <regime_tag>: <count> tasks fail because <capability gap>.
  Current infra returns <inadequate result>. PRIORITY: HIGH|MED|LOW
  (repeat for each identified regime)

## Verified Capabilities (from research_log)
- <approach>: <what it covers> ✓ (cycle N)

## Unresolved
- <regime>: <why it's stuck> (cycle N)

## Human Requests
- (none this cycle)
```

The analyst discovers regimes from task text — NOT from a
hardcoded list. Different benchmarks surface different regimes:
FutureX may surface "finance", "sports", "chinese_content";
PolyBench may surface "code_generation", "mathematical_reasoning";
CTF-Dojo may surface "binary_analysis", "web_exploitation".

### Phase 2: Research (N parallel agents, sandbox + network)

**Agents:** 1 per top-K gap from task board (K=3 default)

**Each agent is assigned a DATA SOURCE REGIME, not a specific API.**
The analyst identifies regimes from failure patterns (e.g. "financial
tasks fail because no exact price data"). The research agent explores
the ENTIRE regime: tests multiple APIs, evaluates coverage breadth,
and identifies which combination of sources covers the most task types
within that regime.

**Each agent:**
1. Reads the regime assignment + sample failing tasks from task board
2. Reads `research_log.jsonl` to avoid retesting known approaches
3. Tests MULTIPLE potential sources in the sandbox, evaluating:
   - Coverage: what kinds of queries does this source handle?
   - Reliability: does it work consistently? Latency?
   - Complementarity: what does this source cover that others don't?
4. Writes structured records to `research_log.jsonl` — one per
   source tested, with regime and coverage metadata

**Research record schema:**
```json
{
  "cycle": 3,
  "regime": "<regime_tag from task board>",
  "approach": "<tool, API, technique, or method name>",
  "endpoint": "<URL, command, or invocation pattern>",
  "tested": true,
  "works": true,
  "latency_ms": 450,
  "coverage": ["<subtypes this approach handles>"],
  "does_not_cover": ["<subtypes it fails on>"],
  "complementary_to": ["<other approach (covers X)>"],
  "sample_output": "<first few lines of output>",
  "credential_needed": false,
  "credential_env": "",
  "error": "",
  "notes": "<how to use, pairing suggestions, caveats>"
}
```

**The research agent's goal is NOT "find one approach that works."**
It is: "map the coverage landscape for this regime so the builder
can construct a pipeline with fallback chains." A good research
cycle tests MULTIPLE approaches within the assigned regime,
recording which subtypes each handles and where they complement
each other.

**Parallel execution:** Research agents work on different regimes
simultaneously. They write to the same `research_log.jsonl` but
each record is self-contained (no cross-agent dependency).

**HITL integration (optional):**
When a research agent discovers an approach needing credentials:
```json
{"regime": "<regime>", "approach": "<name>",
 "works": "unknown", "credential_needed": true,
 "credential_env": "<ENV_VAR>"}
```
The template checks `human_interface`. If enabled, it prompts:
> "Research found <approach> for <regime> but needs credentials.
>  Provide <ENV_VAR> or skip?"

If the human provides the credential, the agent re-tests.
If no HITL or human skips, the approach is logged as
`works: "blocked"`.

### Phase 3: Build (1 agent, sandbox + network)

**Agent:** Builder (full sandbox, reads research_log)

**Reads:**
- `research_log.jsonl` — ONLY entries with `works: true`,
  grouped by regime
- `task_board.md` — priorities and regime categories
- `architecture.md` — what already exists (avoid rebuilding)

**Writes to solver workspace — INFRA PIPELINES, not tool scripts:**

The builder's PRIMARY output is `infra/<regime>_pipeline.py` — one
class-based pipeline per capability regime. Each pipeline:
- Has an `execute(query, **context) -> str` method
- Contains a source/method chain built from verified research
- Routes queries to the best approach for that query subtype
- Includes fallback logic when the primary approach fails
- Handles benchmark-specific context (e.g. date filtering, sandbox
  constraints) internally — the solver doesn't manage it

```python
# infra/<regime>_pipeline.py — ABSTRACT PATTERN (built by builder)
class RegimePipeline:
    """Multi-source resolver for <regime> tasks."""
    
    def execute(self, query: str, **context) -> str:
        parsed = self._parse(query, **context)
        for source in self._source_chain:
            result = source(parsed)
            if result:
                return result
        return ""
    
    # _source_chain is populated from verified research records.
    # Each method wraps ONE approach from the research log.
    # The builder decides the chain order based on coverage breadth
    # and reliability from the research records.
```

The builder ALSO writes:
- `infra/router.py` — top-level router that classifies queries
  by regime and delegates to the right pipeline
- `tools/registry.yaml` — registers pipelines as available tools
- `prompts/system.md` — teaches solver how to use the evolved
  capabilities (without capping tool call counts)

**Writes to evolver workspace:**
- Updated `architecture.md` documenting pipeline architecture:
  which regimes are covered, which approaches in each chain,
  what coverage gaps remain

**Key rules in builder system prompt:**
- Build PIPELINES under `infra/`, not scripts under `tools/`
- Each pipeline covers a REGIME discovered by the analyst —
  not a single API endpoint or tool
- Source/method chains from verified research: primary → secondary
  → fallback
- Every pipeline method must handle errors and return "" on failure
- Never limit the solver's tool call count in the system prompt
- Only build from VERIFIED research results (works: true)
- Keep prompt under 10K characters
- Design for generalization within the regime: a pipeline should
  handle diverse query subtypes within its regime, not just the
  specific instances seen in the current batch

**`tools/` vs `infra/` — the key distinction:**

`tools/` contains independent, self-contained scripts. Each file
does one thing (e.g. `news_search.py` fetches Google News RSS).
The solver calls them explicitly by name. They have no shared
state, no imports between each other, and no awareness of the
broader system.

`infra/` is a software ecosystem. Pipelines under `infra/` can
import and compose tools from `tools/`, orchestrate them with
routing logic, manage shared state (caches, rate limiters,
credentials), and present a unified interface to the solver.
An infra pipeline might load three tools from `tools/`, add
query reformulation and content extraction stages around them,
handle retries and fallbacks between them, and return
agent-friendly formatted output — all behind a single
`execute()` call.

The relationship is analogous to libraries vs applications:
`tools/` are libraries (small, focused, reusable), `infra/` is
the application that wires them together into a working system.

**Why infra is critical:**
The solver calls `tools/` explicitly — it must know each tool name
and decide which to use. `infra/` pipelines are implicit: the
framework invokes them automatically, and the solver interacts
through a single entry point without knowing the internals. This
means:
1. New regimes added by evolution are automatically available
   to the solver without prompt changes
2. Approach upgrades (swapping one source for a better one)
   don't change the solver's behavior
3. Fallback chains and rate limiting handle failures gracefully
   behind the scenes
4. The solver's context window isn't wasted on tool selection

**Why this matters for evolution:**
5. New tools added to `tools/` can be absorbed by existing
   infra pipelines without changing the solver
6. The infra layer handles cross-cutting concerns (rate limiting,
   content formatting, error recovery) once, not per-tool
7. Evolution can improve the ecosystem incrementally: add a tool
   in one cycle, integrate it into the pipeline in the next

**HITL integration (optional):**
Before building, the task board is shown to the human. Human can
add entries or adjust priorities.

### Phase 4: Verify (agent + programmatic loop)

**Agent:** Verifier (sandbox + network)

**For each new/modified tool or infra pipeline:**
1. Run with 3 sample queries derived from batch tasks
2. Check: does it return non-empty data?
3. Check: is the data plausible? (LLM semantic check)
4. Check: does date filtering work? (query with old cutoff)
5. Check: does error handling work? (query with invalid input)

**On failure:**
- Feed verification report back to Builder
- Builder retries with the specific failure context
- Max 3 retries per tool

**On success:**
- Commit tool to solver workspace
- Append `tool_test` record to `research_log.jsonl`

**Loop structure:**
```
Builder writes tool
  → Verifier tests (3 queries + semantic check)
    → PASS: commit, log success, next tool
    → FAIL: feed report to Builder
      → Builder rewrites
        → Verifier tests again
          → PASS: commit
          → FAIL: retry (max 3)
            → 3 failures: remove tool, log failure, skip
```

**Why the verifier is an LLM agent (not just subprocess):**
A subprocess can check "exit code 0 and non-empty output." But:
- "Is 6068.50 a plausible DJIA close price?" requires reasoning
- "This returned a Wikipedia article about Bitcoin history, but
  the task asked for the current price" requires semantic judgment
- "The date filter returned content from 2027, which is after the
  cutoff" requires date reasoning

The guardrails (`_guardrails.py`) handle the programmatic checks.
The verifier agent handles the semantic checks.

## Evolution workspace helpers

New module: `templates/_evolution_workspace.py`

```python
def init_evolution_workspace(ws_root: Path) -> None:
    """Create evolver workspace structure if missing."""

def load_task_board(ws_root: Path) -> str:
    """Read task_board.md content."""

def update_task_board(ws_root: Path, content: str) -> None:
    """Write updated task_board.md."""

def load_research_log(ws_root: Path) -> list[dict]:
    """Load all research records."""

def append_research(ws_root: Path, record: dict) -> None:
    """Validate and append a research record."""

def validate_research_record(record: dict) -> bool:
    """Check required fields: cycle, gap, approach, tested, works."""

def get_verified_approaches(ws_root: Path) -> list[dict]:
    """Return only records with works=True."""

def get_failed_approaches(ws_root: Path) -> list[dict]:
    """Return records with works=False (avoid retesting)."""

def load_architecture(ws_root: Path) -> str:
    """Read architecture.md."""

def update_architecture(ws_root: Path, content: str) -> None:
    """Write updated architecture.md."""

def append_insight(ws_root: Path, record: dict) -> None:
    """Append cross-cycle insight."""
```

## Agent system prompts

### Analyst
```
You are a failure analyst. Read the batch trajectories and the
evolution workspace to identify what's failing and why.

Update task_board.md with:
1. New failure patterns (grouped by data source regime)
2. Priority assessment (HIGH/MEDIUM/LOW based on task count)
3. Cross-reference with research_log — note which gaps already
   have verified solutions vs which need new research

Do NOT suggest solutions. Your job is diagnosis only.
```

### Research Agent
```
You are a research agent investigating: {gap_description}

Already tested (from research_log): {known_results}

Your job: find a working data source for this gap.
1. Test the approach in your sandbox with real HTTP calls
2. Record EXACTLY what endpoint you called, what came back,
   and whether it's usable
3. If the API needs a key, record that — don't fake results

Write your findings as JSON to stdout (one record per test):
{"cycle": N, "gap": "...", "approach": "...", "tested": true,
 "works": true/false, "endpoint": "...", "sample_output": "...",
 "api_key_needed": false, "error": ""}
```

### Builder
```
You are an infrastructure builder. Read the research log and
task board, then build infra pipelines for the solver workspace.

RULES:
1. Only build from VERIFIED research results (works: true)
2. Never limit the solver's tool call count in the system prompt
3. Build class-based pipelines under infra/<regime>_pipeline.py
4. Each pipeline has execute(query, **context) -> str
5. Source chains ordered by coverage breadth + reliability
6. Keep prompts/system.md under 10K characters
7. Update architecture.md with what you built and why
8. Design for regime generalization, not specific instances

{benchmark_builder_hints}
```

### Verifier
```
You are a verification agent. Test each new tool thoroughly.

For each tool, run 3 tests:
1. A realistic query from the batch tasks
2. An edge case (very old date, unusual characters)
3. An error case (empty query, invalid date)

For each test, evaluate:
- Does it return data? (not just "No results")
- Is the data plausible? (right order of magnitude, right format)
- Does date filtering work? (no future data leaking in)

Report: PASS or FAIL with specific evidence.
```

## Implementation guidelines

**Location:** All new template code goes under
`agent_evolve/algorithms/navigation/templates/`. This is where
existing V1/V2 templates live (`verified.py`, `deep_single.py`,
etc.) and where the dynamic loader imports from.

**Minimal, solid, elegant edits.** Prefer the smallest correct
change over a comprehensive rewrite. Do not refactor surrounding
code, add abstractions for hypothetical reuse, or reorganize
imports in files you didn't need to touch. Existing tests (280+)
must keep passing — if an edit risks breaking unrelated code,
it's too broad. New code should follow the patterns already
established by `base.py`, `_guardrails.py`, and existing
templates. Edits must not affect other benchmarks (CTF-Dojo,
PolyBench) — their solvers, configs, and seed workspaces must
remain untouched.

**Existing infrastructure to reuse (do NOT reimplement):**
- `EvolutionTemplate` base class (`templates/base.py`)
- `_guardrails.py` helpers (G2-G5)
- `_run_llm(prompt, workspace_root)` for sandboxed LLM calls
- `AgentWorkspace` for workspace reads/writes
- `HumanInterface` for HITL (`engine/human_interface.py`)
- `VersionControl` for git operations

## Implementation task breakdown

### Phase 0: Helpers + prerequisites

| # | Task | Tag | AC | Notes |
|---|---|---|---|---|
| 0a | Implement `_evolution_workspace.py` | coding | AC2 | Helpers for task board, research log, architecture, insights |
| 0b | Unit tests for workspace helpers | coding | AC2, AC7 | Schema validation, load/append, verified/failed filtering |
| 0c | Verify HITL interface exists and works | coding | AC4 | `engine/human_interface.py` — mock test for API key prompt |

### Phase 1: Template implementation

| # | Task | Tag | AC | Notes |
|---|---|---|---|---|
| 1a | Implement `templates/structured_evolution.py` | coding | AC1 | 4-phase orchestrator, ~400 LOC |
| 1b | Phase 1 (analyze): analyst agent | coding | AC1 | CallLLMSimple, writes task_board.md |
| 1c | Phase 2 (research): parallel dispatch | coding | AC1 | ThreadPoolExecutor, per-gap agents, writes research_log |
| 1d | Phase 3 (build): builder agent | coding | AC1 | Reads verified research, writes solver workspace |
| 1e | Phase 4 (verify): build-verify loop | coding | AC1, AC3 | Verifier agent + retry logic, max 3 attempts |
| 1f | HITL integration points | coding | AC4 | Phase 2 API keys + Phase 3 task board human entries |

### Phase 2: Testing

| # | Task | Tag | AC | Notes |
|---|---|---|---|---|
| 2a | Pipeline test: 4-phase trajectory | coding | AC1, AC7 | Fake engine, verify all 4 phases in trajectory |
| 2b | Build-verify loop test | coding | AC3, AC7 | Broken tool → reject → retry → accept |
| 2c | Research log accumulation test | coding | AC2, AC7 | Run 2 cycles, verify log grows with no duplicates |
| 2d | HITL mock test | coding | AC4, AC7 | Mock human_interface, verify API key prompt fires |
| 2e | Full test suite | coding | AC7 | 280+ tests pass |

### Phase 3: Smoke experiment (FutureX)

| # | Task | Tag | AC | Notes |
|---|---|---|---|---|
| 3a | Create `structured_evolution_evo.yaml` config | coding | AC5 | `orchestrator: structured_evolution` + FutureX hints |
| 3b | Create `experiments/futurex/evolver_hints.md` | coding | AC5 | FutureX-specific regime/research/builder hints |
| 3c | Run 84-task FutureX smoke | coding | AC5 | nohup, wait for completion |
| 3d | Verify evolution workspace artifacts | coding | AC6 | task_board, research_log, architecture exist with content |
| 3e | Collect metrics | coding | AC5 | Pass rate, bash calls/task, regime coverage |
| 3f | Compare with H1 baseline | analyze | AC5 | Same-task comparison on overlapping tasks |

### Phase 4: Iterate if needed

| # | Task | Tag | AC | Notes |
|---|---|---|---|---|
| 4a | Analyze failure patterns from smoke | analyze | — | What did the research agents discover? What did they miss? |
| 4b | Fix bugs in template based on production trajectories | coding | — | Common: research agent format issues, verifier too strict |
| 4c | Rerun if needed | coding | AC5 | Only if bugs found |

## Experiment config

```yaml
# experiments/futurex/configs/structured_evolution_evo.yaml
orchestrator: structured_evolution
builtin_search: strict
sandbox_network: bridge
evolver_sandbox_network: bridge
structured_evolution:
  benchmark_hints: experiments/futurex/evolver_hints.md
  research_parallel: 3        # top-K gaps from task board
  build_verify_retries: 3     # max retries per pipeline
  hitl_enabled: false         # set true for human-in-the-loop
```

## Run commands

```bash
# 84-task FutureX smoke (503 tasks, stride 6)
nohup python solve_all_with_evolution.py \
  --benchmark futurex \
  --seed-workspace experiments/futurex/seed \
  --evolver-prompt experiments/futurex/evolver_prompt.md \
  --config experiments/futurex/configs/structured_evolution_evo.yaml \
  --temporal-reveal \
  --task-timeout 300 \
  --workers 10 \
  --max-turns 80 \
  --limit 503 \
  --stride 6 \
  --batch-size 10 \
  --evolver-temp 0 \
  --solver-temp 0 \
  --output-dir results/futurex_smoke_structured_evo \
  > logs/futurex_structured_evo.log 2>&1 &
echo "Started structured_evolution (PID $!)"
```

## Expected comparison table

| Experiment | Template | Pass rate | vs H1 | Key question |
|---|---|---|---|---|
| H1 (baseline) | single-agent | 36.9% | — | Does evolution help? |
| V1 best | verified | 42.9%* | +6pp* | *Different dataset (56 tasks) |
| V2 best | orthogonal_pair | 36.9% | tie | Can multi-agent match? |
| **V3** | **structured_evolution** | **?** | **target: >36.9%** | Does process-driven multi-agent with infra pipelines beat H1? |

## Key metrics

1. **Pass rate** vs H1 (36.9% on 84-task set)
2. **Avg bash calls/task** (H1=13.3; must not throttle below this)
3. **Network success rate** (>80%; evolved pipelines return real data)
4. **Data source regime coverage** — how many distinct regimes have
   working pipelines (target: ≥4)
5. **System prompt size** — sweet spot is 6-10K chars
6. **Research efficiency** — unique approaches tested per cycle
7. **Build-verify pass rate** — % of pipelines that pass verification
   on first attempt vs after retries

## Files created by this plan

```
agent_evolve/algorithms/navigation/templates/structured_evolution.py
agent_evolve/algorithms/navigation/templates/_evolution_workspace.py
experiments/futurex/configs/structured_evolution_evo.yaml
experiments/futurex/evolver_hints.md
tests/test_structured_evolution.py
tests/test_evolution_workspace.py
```

## Benchmark-specific hints

The template is benchmark-agnostic. Each benchmark provides hints
that customize agent prompts without changing the template logic.

Hints are passed via `{benchmark_*_hints}` placeholders in agent
system prompts. The experiment config specifies the hint file:

```yaml
structured_evolution:
  benchmark_hints: experiments/<benchmark>/evolver_hints.md
```

Example hint files per benchmark:

**FutureX** (`experiments/futurex/evolver_hints.md`):
- Analyst: "Regimes may include finance, sports, chinese_content,
  politics, technology. Tasks require web search with date cutoff."
- Research: "Test APIs with real HTTP requests. Check date
  filtering. Common sources: financial data APIs, Chinese search
  engines, sports statistics APIs, news aggregators."
- Builder: "Pipelines take `cutoff_date` in context. The solver
  calls `web_search(query)` which routes through infra."

**PolyBench** (`experiments/polybench/evolver_hints.md`):
- Analyst: "Regimes may include algorithm_design, data_processing,
  mathematical_reasoning. Tasks require code generation."
- Research: "Test code patterns and library APIs in sandbox.
  Evaluate correctness, edge cases, and performance."
- Builder: "Pipelines provide utility functions and templates.
  The solver calls `bash` to run code."

**CTF-Dojo** (`experiments/ctf_dojo/evolver_hints.md`):
- Analyst: "Regimes may include binary_exploitation, web_security,
  cryptography, reverse_engineering."
- Research: "Test exploitation techniques and tools in sandbox.
  Evaluate reliability and automation potential."
- Builder: "Pipelines provide analysis tools and technique
  templates. The solver calls `bash` to execute."

## Risk assessment

| Risk | Mitigation |
|---|---|
| Research agents discover nothing new | Seed the research prompt with regime categories (not specific approaches) — benchmark hints guide what to explore |
| Build-verify loop never converges | Max 3 retries + fallback to removing the pipeline |
| Evolution workspace grows too large | Cap task_board at 5K chars, research_log at 200 records per cycle |
| HITL blocks automated runs | HITL is optional — disabled by default, research agents log `credential_needed` and move on |
| Parallel research agents conflict | Each writes to research_log.jsonl (append-only, no conflicts); they read shared state but write independent records |
| Template too generic to be useful | Benchmark hints provide domain knowledge without hardcoding it in the template |
