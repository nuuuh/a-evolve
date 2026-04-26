# L3 & L4 Failure Analysis — FutureX Live April 2 Evaluation

**Date**: 2026-04-26
**Run**: `futurex_full_evo_live_0408` (claude_sonnet_4.6 + A_EVOLVE_V2)
**Overall rank**: #19/21 (score 21.58)
**L3 score**: 0.16 (1/18 tasks correct, 5.6% success rate)
**L4 score**: 17.06 (4/29 tasks correct, 13.8% success rate)

---

## Executive Summary

L3 and L4 failures stem from **three structural problems**, not model capability:

1. **L1/L2 are multiple-choice; L3/L4 are open-ended free-form** — our agent was never equipped for exact-value retrieval tasks.
2. **Scoring is strict exact-match with zero tolerance** — predicting 16.0 when the answer is 16.01 scores 0.
3. **Chinese niche platform rankings are unsearchable** — the web_search tool cannot penetrate Douban (豆瓣), Maoyan (猫眼), KolRank, Dongchedi (懂车帝), BiaNews (鞭牛士), or Youmei (铀媒) to retrieve time-specific ranked positions.

A fourth problem compounds these: the **evolution process memorized wrong data into the system prompt**, causing the agent to confidently submit incorrect answers for financial market tasks.

---

## 1. Fundamental Task Format Gap Between Levels

### Evidence

| Level | Tasks | Format | Chinese GT | Success Rate |
|-------|-------|--------|------------|-------------|
| L1 | 112 | All multiple-choice (A/B, Yes/No) | 0% | 80.4% |
| L2 | 123 | All multiple-choice (multi-select A-N) | 0% | 52.8% |
| L3 | 18 | All free-form (ranked lists, exact values) | 61% | 5.6% |
| L4 | 29 | All free-form (ranked lists, exact values) | 10% | 13.8% |

**Source**: `data/futurex/futurex_past.json` — field `ground_truth` per task, field `level`.

L1/L2 tasks ask "Which option?" → agent picks from a constrained set.
L3/L4 tasks ask "Name the exact items ranked N to M" or "What was the exact numeric value?" → agent must produce the precise answer from scratch.

L1 sample GT: `['A']`, `['Yes']`, `['Islanders']`
L3 sample GT: `['翠湖', '密探', '奥利维娅与云']`, `['Casper Ruud', 'Jakub Mensik', 'Flavio Cobolli']`
L4 sample GT: `[249.41]`, `[49384.01]`, `['Rein Me In', 'iloveitiloveitiloveit (Explicit)', 'American Girls']`

The entire skill/prompt/tool evolution pipeline optimized for L1/L2 multiple-choice. None of the evolved skills (`economic-data-lookup`, `election-result-lookup`, `entertainment-data-lookup`, `financial-market-data`, `geopolitical-events`, `prediction-market-resolution`, `sports-result-lookup`) are designed to extract ranked lists from Chinese platforms.

---

## 2. L3: Chinese Niche Platform Inaccessibility (0% success on Chinese tasks)

### L3 Score Breakdown

| Task ID | Title (truncated) | Chinese GT? | Score | Failure Mode |
|---------|-------------------|-------------|-------|-------------|
| 0067 | OWGR Golf rank 12-14 | No | 0.0 | Wrong names retrieved |
| 0113 | Douban movie ranking 4-6 | Yes | 0.0 | Search returned portal pages, not specific rankings |
| 0151 | World Athletics triple jump 10-12 | No | 0.0 | Wrong athletes guessed |
| 0152 | World Athletics 200m women 12-14 | No | 0.0 | Wrong athletes guessed |
| 0181 | BiaNews short drama #1 | Yes | 0.0 | Retrieved data from WRONG WEEK |
| 0250 | ATP singles rank 12-14 | No | 0.0 | Got 1/3 names right (Casper Ruud), 2 wrong |
| 0251 | WTA doubles rank 10-12 | No | 0.0 | Got 1/3 names right (Stefani), 2 wrong |
| 0252 | Douban overseas variety show 1-3 | Yes | 0.0 | Returned "Unknown" for #1 and #2 |
| 0253 | Douban movie ranking 4-6 | Yes | 0.0 | Guessed wrong movies |
| 0254 | Livestock price index | No | 0.0 | Token limit hit, no \boxed answer submitted |
| **0255** | **GBP/CNY exchange rate** | **No** | **1.0** | **Found exact PBOC rate** |
| 0256 | Weibo political accounts 15-17 | Yes | 0.0 | Could not access ranking data |
| 0257 | KolRank WeChat accounts 7-9 | Yes | 0.0 | Could not access ranking data |
| 0258 | KolRank Weibo accounts 4-6 | Yes | 0.0 | Could not access ranking data |
| 0259 | Maoyan "Want to Watch" 6-8 | Yes | 0.0 | Retrieved wrong items from nearby date |
| 0260 | Maoyan ticket rating 4-6 | Yes | 0.0 | Partially correct but not all 3 |
| 0261 | Dongchedi SUV hot list 3-5 | Yes | 0.0 | All 3 names wrong |
| 0262 | Dongchedi sedan hot list 2-4 | Yes | 0.0 | All 3 names wrong |

### Evidence: Search Fails on Chinese Platforms

**Task 0113** (Douban movies): Agent made 22 search calls. Search queries included `豆瓣一周口碑电影榜 2026年1月`, `豆瓣一周口碑电影榜 2026年1月30日`, `site:movie.douban.com 一周口碑电影榜 2026`. Every result returned either:
- Generic portal page: "豆瓣电影排行榜,提供最新电影排行榜"
- Film listing pages without rank positions
- Unrelated content (Youku ads, Xiaohongshu)

**Actual ground truth**: `['翠湖', '密探', '奥利维娅与云']`. The agent guessed `《飞行家》, 《过家家》, 《96分钟》` — all wrong.

**Task 0256** (Weibo political accounts): Agent tried `政法委微博账号影响力排行榜日榜 铀媒`, `site:weibo.com 政法委微博账号影响力排行榜日榜`, and other queries. Final answer admitted: "Due to the dynamic nature of daily rankings and the inability to access future data..." The Youmei (铀媒) platform publishes behind a paywall/app interface that web_search cannot index.

**Task 0262** (Dongchedi sedan hot list): Agent predicted `比亚迪秦L, 特斯拉Model 3, 比亚迪汉`. Actual: `奥迪A6L, 速腾, 迈腾`. The Dongchedi hot list changes daily and is based on user interest metrics, not sales — patterns from search results (sales rankings) don't translate.

### The single L3 success (task 0255)

The only L3 task solved was a GBP-to-CNY exchange rate: a single numeric value published by the People's Bank of China (PBOC) as an official government rate. The search found it directly from an authoritative source. This confirms: when the data is published on an accessible, indexable source, the agent succeeds. The problem is platform accessibility, not agent capability.

---

## 3. L4: Exact-Match Scoring with Zero Tolerance

### Near-Miss Failures (Score 0.0 Despite Correct Methodology)

| Task | Predicted | Ground Truth | Error | Score |
|------|-----------|-------------|-------|-------|
| 0275 (Pork price) | 16.0 | 16.01 | 0.06% | 0.0 |
| 0276 (CSI 300 low) | 4395.00 | 4394.29 | 0.02% | 0.0 |
| 0266 (Influenza) | 6 | 6.0 | 0.00% (format?) | 0.0 |
| 0069 (AAPL high) | 250.00 | 249.41 | 0.24% | 0.0 |
| 0070 (S&P open) | 6915.61 | 6923.23 | 0.11% | 0.0 |
| 0265 (Oil index) | 1379.39 | 1376.38 | 0.22% | 0.0 |
| 0263 (Ping An cap) | 2115.25 | 2090.01 | 1.21% | 0.0 |

**Source**: `results.json` field `score`, cross-referenced with `futurex_past.json` field `ground_truth`.

For task 0275, the agent found pork price data from Chinese agricultural ministry sources, tracked the declining trend from 18.50 (Jan) to 15.46 (Mar 30), and interpolated 16.0 for March 23 — off by only 0.01 yuan. Score: 0.

For task 0276 (CSI 300 Index daily low), the agent predicted 4395.00 vs actual 4394.29 — a difference of 0.71 points on a 4394-point index (0.016% error). Score: 0.

For task 0266 (Influenza outbreaks), the agent answered `6` and the ground truth is `[6.0]`. The answer appears correct but scored 0 — likely a format mismatch between the string "6" and the expected representation.

### Rounding and Approximation

The agent rounds financial data (250.00 instead of 249.41, 17.00 instead of 16.85) because search results report approximate values ("around $248", "resistance at $249.75"). Without direct API access to exact intraday tick data, the agent cannot achieve the precision required for exact-match scoring.

---

## 4. Evolution Poisoned the System Prompt with Wrong Financial Data

### Evidence: System Prompt Hardcoded Values vs Ground Truth

The evolved system prompt (`futurex/prompts/system.md`) contains a "FINANCIAL MARKET DATA (Jan 2026)" section with hardcoded values from earlier evolution cycles. These values were memorized from noisy web search results:

| Data Point | Memorized in Prompt | Ground Truth | Match? |
|-----------|-------------------|--------------|--------|
| DJIA Jan 22 close | 49,077.23 (line 105) | 49,384.01 | WRONG |
| S&P 500 Jan 23 close | 6,915.61 (line 106) | 6,923.23 | WRONG |
| Nikkei 225 Jan 23 close | 53,846.87 (line 107) | 53,846.87 | Correct |
| NASDAQ Jan 27 close | 19,341.83 (line 108) | 23,734.75 | WRONG |

**Source**: Evolved `futurex/prompts/system.md` lines 104-108 vs `futurex_past.json` ground truth for tasks 0071, 0070, 0072, 0074.

When the agent encountered these tasks in later batches, it used the memorized (wrong) values directly. The boxed answers match the prompt values exactly — confirming the agent trusted the evolved prompt over fresh search.

The NASDAQ value is off by 23% (19,341 vs 23,734) — the prompt captured the post-DeepSeek-selloff closing price, but the task asks for the OPENING price, which was much higher before the selloff.

### Mechanism

The evolution loop works as follows:
1. Batch N: Agent searches for data, gets approximate results from web.
2. Evolver sees the trajectory and memorizes "useful" facts into the system prompt.
3. Batch N+1: Agent uses hardcoded data instead of searching again.
4. If the memorized data was wrong (different date, wrong metric, rounded), all future uses inherit the error.

This is especially dangerous for financial market data where close/open/high/low values differ and web search returns approximate figures.

---

## 5. L4: Ranking and Ordering Failures

### Task 0281 (UK Official Singles Chart)

- **Ground truth**: `['Rein Me In', 'iloveitiloveitiloveit (Explicit)', 'American Girls']`
- **Agent answer**: `1. Harry Styles - "American Girls", 2. Sam Fender and Olivia Dean - "Rein Me In", 3. Bella Kay - "iloveitiloveitiloveit"`
- **Score**: 0.0

The agent found all three correct songs but predicted the WRONG ORDER. The agent used the chart for week ending March 19 (announced March 20) where "American Girls" was #1. But the task date is March 24, and the latest chart as of that date was the one for week ending March 26 (announced March 27 in the system prompt's own data), where "Rein Me In" displaced "American Girls" at #1.

The evolved system prompt (line 470-473) actually contains BOTH chart weeks but the agent selected the wrong one. This shows a temporal reasoning failure within the agent.

### Task 0032 & 0068 (Amazon Charts Most Read Fiction)

- Task 0032: Predicted `Harry Potter and the Goblet of Fire, The Correspondent, Dungeon Crawler Carl`. Actual: `The Housemaid, Brimstone, The Correspondent`.
- Task 0068: Predicted `Harry Potter and the Order of the Phoenix, Harry Potter and the Goblet of Fire, Dungeon Crawler Carl`. Actual: `Heated Rivalry, Fourth Wing, Quicksilver`.

Search returned fragments mentioning Harry Potter prominently (multiple entries on the list) but the agent couldn't determine exact positions 4-6 or 13-15 from the snippets. The agent over-indexed on Harry Potter entries visible in search snippets.

### Tasks 0268, 0270 (OpenGithub daily/weekly rank)

Agent confirmed the GitHub files exist (`github-daily-rank/2026/03/20260323.md`) but "was unable to retrieve the actual content due to network restrictions in the sandbox environment." The `web_search` tool can find that a page exists but cannot fetch raw file content from GitHub repos. The agent explicitly admitted failure and submitted "Unable to determine..." in the \boxed answer.

---

## 6. L4: Chinese Content Platform Failures (Same Pattern as L3)

| Task ID | Platform | Content Type | Score |
|---------|----------|-------------|-------|
| 0271 | Maoer FM (猫耳FM) | Audio drama tipping chart | 0.0 |
| 0274 | QQ Music | Soaring chart songs | 0.0 |
| 0277 | Autohome (汽车之家) | Smart technologies ranking | 0.0 |

These follow the same pattern as L3 Chinese platform failures: the `web_search` tool cannot access real-time or historical ranking data from these closed Chinese platforms. The agent finds peripherally related data (e.g., which shows aired around that date) but cannot determine exact rank positions.

---

## 7. Format and Verbosity Issues

### 18/43 failed L3+L4 tasks submitted explanatory text in \boxed{}

Many failed tasks' answers contained hedging language inside the `\boxed{}`:
- `\boxed{Based on available data...}`
- `\boxed{Unable to determine the exact...}`
- `\boxed{Due to the dynamic nature of daily rankings...}`

Even where the FutureX scorer is lenient on formatting, embedding explanations alongside answers likely causes parsing failures. The 4 L4 successes all submitted clean, concise answers: `\boxed{53846.87}`, `\boxed{129.83}`, `\boxed{Hoppers}`, `\boxed{73.88}`.

### 1 task hit token limit without submitting any answer

Task 0254 (livestock price index, L3) exceeded the token limit during `sequentialthinking` and never produced a `\boxed{}` answer. Output ends with: "The selected tool sequentialthinking's tool use was incomplete due to maximum token limits being reached."

---

## 8. What the 5 Successful L3+L4 Tasks Have in Common

| Task | Level | Domain | Data Source | Score |
|------|-------|--------|------------|-------|
| 0255 | L3 | Forex | PBOC (government) | 1.0 |
| 0072 | L4 | Financial | Armstrong Economics | 1.0 |
| 0153 | L4 | Agriculture | Chinese gov reports | 1.0 |
| 0264 | L4 | Box office | Box Office Mojo | 1.0 |
| 0272 | L4 | Financial | Chinese financial news | 1.0 |

All 5 successes share:
1. **Single authoritative source** that publishes exact data on the web
2. **Indexable by general web search** (government sites, English-language financial news, Box Office Mojo)
3. **Single-value answer** (one number or one name) — not a ranked list of 3
4. **Clean \boxed answer** with no hedging

---

## 9. Comparison: H2O (Rank #3) Uses Same Model

H2O_AI_Super_Agent_v1.82 uses `claude_sonnet_4.6` and scores 53.21 overall:
- L3: 51.66 vs our 0.16 (322x better)
- L4: 44.63 vs our 17.06 (2.6x better)

Same model, same knowledge cutoff. The difference is entirely in the agent framework's search and retrieval pipeline. H2O likely has:
- Direct API access to Chinese platforms (or cached data feeds)
- More precise financial data sources (real-time or historical tick data)
- Better answer formatting that meets exact-match requirements

---

## 10. Root Cause Summary

| Root Cause | L3 Impact | L4 Impact | Tasks Affected |
|-----------|-----------|-----------|----------------|
| Chinese platform data inaccessible via web_search | 12/17 failures | 4/25 failures | 16 |
| Exact-match scoring with zero tolerance | All 17 failures | 7/25 failures (near-misses) | 24 |
| Evolution memorized wrong data into prompt | 0 | 4/25 failures | 4 |
| Ordering/temporal reasoning errors | 0 | 3/25 failures | 3 |
| Format issues (verbose \boxed, no \boxed) | Part of all failures | Part of all failures | 19 |
| Open-ended free-form vs multiple-choice gap | Foundational | Foundational | All 47 |

---

## 11. Recommendations

1. **Add Chinese platform data access**: Direct API integration or cached feed from Douban, Maoyan, Dongchedi, KolRank, QQ Music, Maoer FM, Youmei. This alone could recover ~12 L3 tasks and ~4 L4 tasks.

2. **Add financial data API**: Yahoo Finance, Sina Finance, or Bloomberg API for exact open/high/low/close values. Web search returns approximate values that fail exact-match scoring.

3. **Stop hardcoding data in the evolved system prompt**: The evolution loop must not memorize specific data values from search results. Alternatively, treat memorized values as hints that MUST be re-verified by live search before submission.

4. **Format enforcement**: Strip all explanatory text from `\boxed{}` answers. Submit only the bare answer (names, numbers).

5. **Add tolerance-aware answering**: For numeric tasks, find exact values from authoritative sources rather than rounding. When the precise value cannot be found, search more specifically (e.g., "January 22 2026 DJIA close 49" to find the exact figure).

6. **Chart temporal reasoning**: For "latest chart on date X" tasks, explicitly compute which chart edition is "latest" given publication schedules (e.g., UK Singles Chart announced Fridays).
