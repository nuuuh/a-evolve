# Multi-Agent Evolution Templates: Performance Report

## Template Descriptions

### Baselines

| Template | Description |
|:--|:--|
| **H0a** | No search, no evolution. Pure LLM reasoning. |
| **H0b** | Built-in strict search (DuckDuckGo+Wikipedia+htmldate). No evolution. |
| **H1** | Single-agent evolution. One evolver with full sandbox builds tools+prompts in one context window. |

### V1 Templates (56 tasks)

| Template | Architecture |
|:--|:--|
| **A: verified** | Evolver builds → Verifier tests each tool in separate sandbox → removes broken ones. |
| **B: specialists** | 3 agents split by workspace layer: tool builder + prompt writer + memory curator. |
| **C: debate** | Evolver proposes → Critic reviews → Evolver revises. 2-3 debate rounds per cycle. |
| **D: mosaic** | Planner assigns task subsets to branch evolvers → Fuser merges best elements. |
| **E: adaptive** | State machine: inspects workspace state → dispatches to ToolBuilder/Debugger/Strategist/Refiner. |

### V2 Templates (84 tasks)

| Template | Architecture |
|:--|:--|
| **F: scout_evolver** | Scout tests APIs → writes `discoveries.jsonl` → Evolver builds tools only for working sources. |
| **G: deep_single** | H1 + enriched prompt + programmatic post-evolution tool verification + guardrails. Control. |
| **H: discovery_cache** | 2-3 agents share persistent `discovery_cache.jsonl` across agents and cycles. |
| **I: orthogonal_pair** | General tool agent (always) + Domain expert (hard tasks only). Deterministic dispatch. |
| **J: population** | N=3 parallel evolvers with different seeds → Tournament selects → Fusion merges. |

## V1 Results (56-task smoke)

| Template | Pass Rate | vs H1 | Bash/task |
|:--|--:|--:|--:|
| H0a (no search) | 32.1% | -10.8 | 0.0 |
| H0b (strict search) | 35.7% | -7.2 | 10.2 |
| **H1 (single-agent evo)** | **42.9%** | **baseline** | **10.9** |
| A: verified | 42.9% | tie | 7.3 |
| B: specialists | 28.6% | -14.3 | 3.5 |
| C: debate | 35.7% | -7.2 | 11.5 |
| D: mosaic | 37.5% | -5.4 | 6.8 |
| E: adaptive | 30.4% | -12.5 | 3.6 |

## V2 Results (84-task smoke)

| Template | Pass Rate | vs H1 | Bash/task |
|:--|--:|--:|--:|
| **H1 (single-agent evo)** | **36.9%** | **baseline** | **15.6** |
| F: scout_evolver | 34.5% | -2.4 | 11.8 |
| G: deep_single | 26.2% | -10.7 | 13.3 |
| H: discovery_cache | 26.2% | -10.7 | 1.2 |
| **I: orthogonal_pair** | **36.9%** | **tie** | **9.6** |
| J: population | 26.2% | -10.7 | 3.0 |

Note: V1 and V2 ran on different task sets (56 vs 84 tasks). Pass rates are comparable within each generation but not directly across.

---

## L3+L4 Tool Gap Analysis (31 live submission tasks, Sonnet 4.6)

Separate from the evolution experiments above, we tested the effect of search tools and agent framework on the hardest tasks (L3 rankings + L4 numerics) from the April 2 live leaderboard submission, scored with FutureX official formulas (σ-normalized for numerics, 0.8×overlap/k for rankings).

| # | Experiment | Search Tools | L3 | L4 | Weighted |
|---|-----------|-------------|:--:|:--:|:--------:|
| 1 | Baseline (no evo) | DuckDuckGo+Wiki | 9.1% | 17.2% | 9.6% |
| 2 | Evolution (3 cycles) | DuckDuckGo+Wiki | 14.7% | 18.2% | 11.7% |
| 3 | Our Solver + MF Tools | Serper+Jina (our scripts) | 14.3% | 51.1% | 24.7% |
| 4 | Our Solver + LLM Filter | Serper+Jina (our scripts) | 18.8% | 34.7% | 19.5% |
| **5** | **MiroFlow Official** | MiroFlow MCP Serper+Jina | **13.9%** | **60.2%** | **28.3%** |
| 6 | MiroFlow LB (GPT-5) | MiroFlow MCP Serper+Jina | 50.8% | 56.4% | ~37% |

Experiments #1-5 ran retroactively (Apr 27-28). #6 ran at correct eval time by the FutureX platform.

## MiroFlow Prompt Design

MiroFlow's +9% L4 advantage (#5 vs #3) comes from its prompt strategy, not tools. Below is the prompt structure with key sections annotated.

### System prompt (from `config/agent_prompts/main_boxed_answer.py`)

```
[Tool format instructions: MCP XML <use_mcp_tool> format, tool schemas]

# General Objective

You accomplish a given task iteratively, breaking it down into clear
steps and working through them methodically.

## Task Strategy

1. Analyze the user's request and set clear, achievable sub-goals.   ← [PLAN FIRST]
2. Start with a concise, numbered, step-by-step plan.
3. Work through sub-goals sequentially. After each step, carefully
   review and extract all potentially relevant information.
4. You have access to a wide range of powerful tools.

## Tool-Use Guidelines

1. **IMPORTANT: Each step must involve exactly ONE tool call only.**  ← [ONE TOOL PER TURN]
2. Before each tool call:
   - Briefly summarize and analyze what is currently known.           ← [THINK BEFORE ACT]
   - Identify what is missing, uncertain, or unreliable.
   - Choose the most relevant tool and explain why.
3. All tool queries must include full, self-contained context.
4. Avoid broad, vague, or speculative queries.
5. **For historical or time-specific content**: Regular search         ← [TEMPORAL AWARENESS]
   engines return current content, not historical. Use archived
   webpage search for past content.
6. Even if a tool result does not directly answer the question,       ← [EXTRACT ALL INFO]
   thoroughly extract and summarize all partial information.

## Tool-Use Communication Rules

1. **CRITICAL: After issuing exactly ONE tool call, STOP your         ← [STOP AFTER ONE CALL]
   response immediately. You must never make multiple tool calls
   in a single response.**
2. Do not present the final answer until the entire task is complete.
3. Unless otherwise requested, respond in the same language as
   the user's message.

## 中文语境处理指导                                                      ← [CHINESE CONTEXT]

当处理中文相关的任务时：
1. 搜索策略: 搜索关键词应使用中文
2. 思考过程: 内部分析、推理、总结等思考过程都应使用中文
3. 信息整理: 从中文资源获取的信息应保持中文原文
4. 各种输出: 所有输出都应使用中文
5. 最终答案: 对于中文语境的问题，最终答案应使用中文回应
```

### Task wrapping (appended to every user message, from `src/core/orchestrator.py`)

```
Your task is to comprehensively address the question by actively       ← [DON'T RUSH]
collecting detailed information from the web. Your goal is NOT to
rush a single definitive answer, but rather to gather complete
information and present ALL plausible candidate answers.

- Collect comprehensive information from reliable sources.            ← [EXHAUSTIVE SEARCH]
- Present every possible candidate answer.
- Explicitly document facts, evidence, and reasoning steps.
- Clearly flag uncertainties, conflicting interpretations.

## 中文任务处理指导                                                      ← [CHINESE SEARCH STRATEGY]

- 信息收集策略：使用中文关键词进行网络搜索，优先浏览中文网页
- 思考过程：所有分析、推理、判断都应使用中文
- 候选答案收集：收集所有可能的中文答案选项
- 证据文档化：保持中文资源的原始格式
```

### Summary prompt (triggered at max turns)

```
Summarize ALL working history. Output FINAL ANSWER in \boxed{...}.
If a definitive answer could not be determined, make a well-informed  ← [ALWAYS COMMIT]
educated guess based on the conversation.
```

## Search Persistence: Turn Count Comparison

| Experiment | Avg turns/task | Avg tool calls/task | Tools per turn | L4 Score |
|:--|:--:|:--:|:--:|:--:|
| Baseline (DuckDuckGo) | 10.8 | ~10 | ~1.0 | 17.2% |
| Our Solver + MF Tools | 13.9 | ~17 | ~1.2 | 51.1% |
| **MiroFlow Official** | **20.1** | **20.1** | **1.0** | **60.2%** |

MiroFlow's "one tool per turn" prompt design produces 20 turns of think→act→observe per task vs our solver's 14. Each turn includes explicit reasoning ("what is known, what is missing") before the next tool call. The +6 turns/task translate to +9% L4 — finding data (Trading value, GitHub ranking, US TV) that our solver gave up searching for.
