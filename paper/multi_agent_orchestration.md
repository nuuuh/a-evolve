# Multi-Agent Orchestration for Evolution

## Structured Evolution: 4-Phase Flow Map

```
                          ┌─────────────────────────────────────────────┐
                          │           SOLVER (Inference Phase)          │
                          │                                             │
                          │  Batch of tasks ──► Solver LLM ──► Results  │
                          │  (uses tools/, infra/, prompts/)            │
                          └──────────────────────┬──────────────────────┘
                                                 │
                                    batch results + trajectories
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                        EVOLUTION PHASE (4 phases per cycle)                        │
│                                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  PHASE 1: ANALYZE                                                            │  │
│  │                                                                              │  │
│  │  Analyst Agent (no sandbox, no network)                                      │  │
│  │    │                                                                         │  │
│  │    │  Reads:                                                                 │  │
│  │    │    • Solver batch trajectories (conversations, tool calls, no scores    │  │
│  │    │      for unrevealed tasks — temporal-reveal privacy)                    │  │
│  │    │    • evolver_workspace/task_board.md (prior cycle's analysis)           │  │
│  │    │    • evolver_workspace/research_log.jsonl (what's been tried)           │  │
│  │    │                                                                         │  │
│  │    │  Does:                                                                  │  │
│  │    │    • Discovers failure REGIMES from task text                           │  │
│  │    │      (e.g. "finance", "chinese_content", "sports_rankings")            │  │
│  │    │    • Classifies each failure by capability gap                          │  │
│  │    │    • Prioritizes gaps: HIGH / MED / LOW                                │  │
│  │    │                                                                         │  │
│  │    ▼                                                                         │  │
│  │  Writes: evolver_workspace/task_board.md                                     │  │
│  │    ┌─────────────────────────────────────────────┐                           │  │
│  │    │ ## Failure Patterns (Cycle N)                │                           │  │
│  │    │ - finance: 8 tasks fail, no exact prices.   │                           │  │
│  │    │   PRIORITY: HIGH                            │                           │  │
│  │    │ - chinese_rankings: 5 tasks, no platform    │                           │  │
│  │    │   access. PRIORITY: HIGH                    │                           │  │
│  │    │ - sports: 3 tasks, stale rankings.          │                           │  │
│  │    │   PRIORITY: MED                             │                           │  │
│  │    │                                             │                           │  │
│  │    │ ## Human Requests                           │                           │  │
│  │    │ - (none this cycle)                         │                           │  │
│  │    └─────────────────────────────────────────────┘                           │  │
│  └──────────────────────────────────┬───────────────────────────────────────────┘  │
│                                     │                                              │
│                          top-K gaps from task_board                                │
│                                     │                                              │
│  ┌──────────────────────────────────▼───────────────────────────────────────────┐  │
│  │  PHASE 2: RESEARCH (N parallel agents, sandbox + network)                    │  │
│  │                                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │  │
│  │  │ Research Agent 1 │  │ Research Agent 2 │  │ Research Agent 3 │             │  │
│  │  │ regime: finance  │  │ regime: chinese  │  │ regime: sports   │             │  │
│  │  │                  │  │                  │  │                  │             │  │
│  │  │ Tests:           │  │ Tests:           │  │ Tests:           │             │  │
│  │  │ • Eastmoney API  │  │ • Douban (Jina)  │  │ • ESPN scrape    │             │  │
│  │  │ • Investing.com  │  │ • Maoyan (Jina)  │  │ • WTA official   │             │  │
│  │  │ • Sina Finance   │  │ • QQ Music       │  │ • Sofascore      │             │  │
│  │  │ • PBOC rates     │  │ • KolRank        │  │ • FlixPatrol     │             │  │
│  │  │                  │  │                  │  │                  │             │  │
│  │  │ If credential    │  │                  │  │                  │             │  │
│  │  │ needed:          │  │                  │  │                  │             │  │
│  │  │ ┌──────────────┐ │  │                  │  │                  │             │  │
│  │  │ │ 🧑 HITL:     │ │  │                  │  │                  │             │  │
│  │  │ │ "Serper API  │ │  │                  │  │                  │             │  │
│  │  │ │  key needed. │ │  │                  │  │                  │             │  │
│  │  │ │  Provide or  │ │  │                  │  │                  │             │  │
│  │  │ │  skip?"      │ │  │                  │  │                  │             │  │
│  │  │ └──────────────┘ │  │                  │  │                  │             │  │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘             │  │
│  │           │                     │                      │                       │  │
│  │           └─────────────────────┼──────────────────────┘                       │  │
│  │                                 ▼                                              │  │
│  │           evolver_workspace/research_log.jsonl (append-only)                   │  │
│  │             {cycle:3, regime:"finance", approach:"Eastmoney",                  │  │
│  │              works:true, latency_ms:450, coverage:["stock_ohlc","market_cap"], │  │
│  │              sample_output:"收盘价: 4636.57..."}                                │  │
│  │             {cycle:3, regime:"chinese", approach:"Douban_Jina",                │  │
│  │              works:true, coverage:["movie_chart","variety_chart"]}             │  │
│  │             {cycle:3, regime:"finance", approach:"DuckDuckGo",                 │  │
│  │              works:false, error:"timeout after 8s on 3/3 queries"}            │  │
│  └──────────────────────────────────┬───────────────────────────────────────────┘  │
│                                     │                                              │
│                     research_log.jsonl (works=true only)                           │
│                                     │                                              │
│  ┌──────────────────────────────────▼───────────────────────────────────────────┐  │
│  │  PHASE 3: BUILD (1 agent, sandbox + network)                                 │  │
│  │                                                                              │  │
│  │  Builder Agent                                                               │  │
│  │    │                                                                         │  │
│  │    │  Reads: verified research + task_board + architecture.md                │  │
│  │    │                                                                         │  │
│  │    │  ┌──────────────────────────────────────────┐                           │  │
│  │    │  │ 🧑 HITL (optional):                      │                           │  │
│  │    │  │ Shows task_board to human before building │                           │  │
│  │    │  │ Human can add entries or adjust priorities │                           │  │
│  │    │  └──────────────────────────────────────────┘                           │  │
│  │    │                                                                         │  │
│  │    │  Writes to SOLVER workspace:                                            │  │
│  │    │    • infra/<regime>_pipeline.py  (multi-source pipeline per regime)      │  │
│  │    │    • infra/router.py            (query classifier → pipeline)           │  │
│  │    │    • tools/registry.yaml        (registers pipelines)                   │  │
│  │    │    • prompts/system.md          (teaches solver, NO search caps)        │  │
│  │    │                                                                         │  │
│  │    │  Writes to EVOLVER workspace:                                           │  │
│  │    │    • architecture.md            (documents what was built)              │  │
│  │    │                                                                         │  │
│  │    ▼                                                                         │  │
│  │  Built tools/pipelines ready for verification                                │  │
│  └──────────────────────────────────┬───────────────────────────────────────────┘  │
│                                     │                                              │
│  ┌──────────────────────────────────▼───────────────────────────────────────────┐  │
│  │  PHASE 4: VERIFY (agent + programmatic loop)                                 │  │
│  │                                                                              │  │
│  │  For each new tool/pipeline:                                                 │  │
│  │                                                                              │  │
│  │    Verifier Agent (sandbox + network)                                        │  │
│  │      │                                                                       │  │
│  │      │  Tests with 3 sample queries:                                         │  │
│  │      │    ✓ Returns non-empty data?                                          │  │
│  │      │    ✓ Data is plausible? (LLM semantic check)                          │  │
│  │      │    ✓ Date filtering works? (query with old cutoff)                    │  │
│  │      │    ✓ Error handling works? (query with invalid input)                 │  │
│  │      │                                                                       │  │
│  │      ├──► PASS ──► Commit to solver workspace                                │  │
│  │      │              Append tool_test record to research_log                   │  │
│  │      │                                                                       │  │
│  │      └──► FAIL ──► Feed verification report to Builder                       │  │
│  │                     │                                                         │  │
│  │                     ▼                                                         │  │
│  │                   Builder rewrites tool with failure context                  │  │
│  │                     │                                                         │  │
│  │                     ▼                                                         │  │
│  │                   Verifier tests again                                        │  │
│  │                     │                                                         │  │
│  │                     ├──► PASS ──► Commit                                      │  │
│  │                     └──► FAIL ──► Retry (max 3)                               │  │
│  │                                    └──► 3 failures: remove tool, log, skip    │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
│                                     │                                              │
│                              Committed workspace                                   │
│                              (tools verified, prompts updated)                      │
│                                     │                                              │
└─────────────────────────────────────┼──────────────────────────────────────────────┘
                                      │
                                      ▼
                               Next solver batch
                            (uses improved workspace)
```

## Agent Roles

| Agent | Phase | Sandbox | Network | Reads | Writes |
|:--|:--|:--:|:--:|:--|:--|
| **Analyst** | 1. Analyze | No | No | Trajectories, task_board, research_log | task_board.md |
| **Researcher** (×N) | 2. Research | Yes | Yes | Task board gaps, research_log | research_log.jsonl |
| **Builder** | 3. Build | Yes | Yes | Verified research, architecture | Solver workspace (infra/, tools/, prompts/) |
| **Verifier** | 4. Verify | Yes | Yes | Built tools, sample queries | Tool test results, research_log |

## Human-in-the-Loop Integration Points

| Phase | Trigger | Human Action | If No Human |
|:--|:--|:--|:--|
| **Phase 2** (Research) | Approach needs API credentials | "Provide SERPER_API_KEY or skip?" | Logged as `works: "blocked"`, skipped |
| **Phase 3** (Build) | Before building starts | Review task_board, add entries, adjust priorities | Builder proceeds with analyst's priorities |

HITL is optional — disabled by default. When enabled, the template checks `human_interface` (supports stdin, Telegram, Slack). Research agents log `credential_needed: true` and the template prompts the human. If the human provides the credential, the agent re-tests. If no response or HITL disabled, the approach is skipped.

## Key Design Decisions

**Workspace separation.** Solver workspace has production artifacts only. Evolver workspace has analysis state. The solver never sees evolver state.

**Research before building.** V1/V2 mixed experimentation with production. Phase 2 tests APIs; Phase 3 only builds from verified results (`works: true`).

**Infra pipelines, not tool scripts.** `tools/` has independent scripts. `infra/` composes them into pipelines with source chains, fallback logic, and routing. New regimes are automatically available without prompt changes.

**Knowledge accumulation.** `research_log.jsonl` persists across cycles. Cycle 3's researcher skips sources that cycle 1 already tested. `task_board.md` accumulates failure patterns. `architecture.md` tracks the built ecosystem.

**Temporal-reveal privacy.** The analyst sees solver behavior (tool calls, turns) for all tasks, but ground-truth labels only for tasks whose resolution date has passed. This prevents the evolver from learning from future information.
