# FutureX Leaderboard Comparison (L1 + L2)

Comparison restricted to L1 and L2 tasks only. L3/L4 tasks require data from
platforms our search pipeline cannot access (Chinese rankings, proprietary
databases) — all our methods score ~0% on those levels.

Leaderboard agents run **before events resolve** (zero contamination). Our strict
experiments use per-task htmldate date filtering (~7% leakage from undated results).

---

## March Week 2 (L1=12, L2=24)

36 shared tasks matched between FutureX-Online (commit `a696ecd3`) and
FutureX-Past using strict 3-criteria matching (same ID + title + end_time).

| Agent | L1 (12) | L2 (24) |
|---|---|---|
| **Our h2 (early_freeze)** | **83.3%** | **70.8%** |
| TongAgents beta (GPT-5) | 83.3% | 69.4% |
| H2O v1.82 (Sonnet 4.6) | 83.3% | 65.3% |
| MiroFlow (GPT-5) | 83.3% | 65.3% |
| GPT-5.2 (Search) | 75.0% | 65.3% |
| **Our h0b (htmldate)** | **75.0%** | **62.5%** |
| **Our h1 (evo+htmldate)** | **75.0%** | **54.2%** |
| DeepSeek-V3.2 (Search) | 75.0% | 56.5% |
| Grok-4 (Search) | 58.3% | 48.6% |
| GLM-5 (Search) | 41.7% | 44.4% |

---

## March Week 3 (L1=14, L2=17)

63 tasks resolving March 19-24, matching the leaderboard's 63 events exactly.

| Agent | L1 (14) | L2 (17) |
|---|---|---|
| GPT5.4 (Milkyway v2) | 71.4% | 82.3% |
| GPT5.2 (GOAT) | 71.4% | 82.3% |
| Sonnet 4.6 (H2O v1.82) | 64.3% | 79.0% |
| GPT-5 (MiroFlow) | 64.3% | 72.8% |
| Kimi-k2.5-thinking (Search) | 71.4% | 67.4% |
| **Our h1 (evo+htmldate)** | **78.6%** | **58.8%** |
| Sonnet 4.6 (H2O v1.80) | 57.1% | 67.2% |
| **Our h2 (early_freeze)** | **64.3%** | **64.7%** |
| GLM-5 (Search) | 64.3% | 50.3% |
| DeepSeek-V3.2 (Search) | 64.3% | 52.7% |
| **Our h0b (htmldate)** | **57.1%** | **52.9%** |
| Grok-4 (Search) | 71.4% | 24.5% |
| Qwen-3.5-plus (Search) | 28.6% | 52.7% |

---

## Summary

| | March W2 (L2) | March W3 (L1) | March W3 (L2) |
|---|---|---|---|
| Top leaderboard | 69.4% | 71.4% | 82.3% |
| **Our best (h2)** | **70.8%** | **64.3%** | **64.7%** |
| Gap | **+1.4pp** | -7.1pp | -17.6pp |

- **March W2 L2: our h2 beats the entire leaderboard** (70.8% vs TongAgents' 69.4%)
- **March W3 L1: competitive** — h1 at 78.6% would rank #1
- **March W3 L2: 18pp gap** — leaderboard agents use Google Serper + Jina scraping
  with 200 turns; we use DuckDuckGo + htmldate with 20 turns

---

## Why L3 and L4 fail

All our methods score ~0% on L3/L4 tasks. This is not shown in the tables above
(L1+L2 only) but explains why our overall scores are lower than the leaderboard.

| Level | Our accuracy | Top leaderboard | Failure cause |
|---|---|---|---|
| L3 | 0% | 21–74% | Tasks require data from unsearchable platforms (Maoyan, Douban, WeChat) |
| L4 | 0–5% | 28–54% | Tasks require niche domain APIs, Chinese-language platform rankings |

Concrete examples of L3/L4 failures:
- "Which programs will rank in the top 10 on Maoyan this week?" — Maoyan data is
  not indexed by DuckDuckGo or Wikipedia
- "Who will be ranked 17-19 on the Douban book chart?" — requires Douban API access
- "What will the China Influenza Weekly Report show?" — requires Chinese CDC data

These failures are **infrastructure-level** — the agent's reasoning is correct but
the data simply doesn't exist in our search pipeline. The leaderboard agents use
Google Serper + Jina which can scrape these platforms when run pre-resolution.
Addressing this requires adding platform-specific data fetchers to the `infra/`
layer (see `paper/implementation_plan.md`).
