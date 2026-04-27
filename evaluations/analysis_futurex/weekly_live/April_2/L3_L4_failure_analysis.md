# L3 & L4 Failure Analysis — FutureX Live April 2 Evaluation

**Date**: 2026-04-27 (revised)
**Run**: `futurex_full_evo_live_0408` (claude_sonnet_4.6 + A_EVOLVE_V2)
**Live leaderboard rank**: #19/21 (overall 21.58)
**Ground truth source**: `futurex-ai/Futurex-Past` on HuggingFace (503 tasks, 410 with GT)
**Submission**: 82 tasks submitted, 66 matched to HF ground truth

## Leaderboard Scores

| Level | Score | Submitted | Matched to GT | Correct | Success Rate |
|-------|------:|----------:|--------------:|--------:|-------------:|
| L1 | 40.00 | 19 | 15 | 7 | 46.7% |
| L2 | 53.52 | 29 | 20 | 9 | 45.0% |
| L3 | 0.16 | 13 | 12 | 0 | 0.0% |
| L4 | 17.06 | 21 | 19 | 1 | 5.3% |
| **Total** | **21.58** | **82** | **66** | **17** | **25.8%** |

---

## 1. Primary Failure Mode: Agent Gives Up (35% of L3+L4 failures)

The single largest failure mode across L3 and L4 is the agent producing hedged, non-committal predictions instead of attempting a concrete answer.

**11 of 31 L3+L4 tasks** contain hedging language:
- "Due to insufficient data..."
- "Unable to determine with confidence..."
- "Based on available data..."
- "Without access to the specific..."
- "I cannot reliably predict..."

These hedged predictions score zero regardless of whether the underlying reasoning has partial merit.

| Hedge Rate | Chinese-prompt tasks | Non-Chinese tasks |
|-----------|--------------------:|------------------:|
| L3+L4 combined | 9/20 = 45% | 4/14 = 29% |

Chinese-prompt tasks have a higher hedge rate (45% vs 29%), but the agent also gives up on non-Chinese tasks like OpenGithub rankings, Apple TV charts, and KolRank WeChat rankings.

---

## 2. Second Failure Mode: Numeric Precision (39% of L3+L4 failures)

12 of 31 L3+L4 tasks require exact numeric values. The agent gets the right order of magnitude but fails exact-match scoring.

### Near-Misses (< 10% error, scored 0)

| Task | Predicted | Ground Truth | Error |
|------|----------:|-------------:|------:|
| Grain/Oil Index | 113.0 | 112.54 | 0.4% |
| CanSino low | 68 | 69.81 | 2.6% |
| India Fund high | 1.43 | 1.329 | 7.6% |
| CSI 300 open | 4,400 | 4,694.43 | 6.3% |

### Large Misses (> 10% error)

| Task | Predicted | Ground Truth | Error |
|------|----------:|-------------:|------:|
| Livestock index | 140 | 116.38 | 20.3% |
| GBP/CNY rate | 720.00 | 924.89 | 22.2% |
| Coastal Oil Index | 1050 | 1,408.44 | 25.4% |
| Influenza outbreaks | 50 | 56.0 | 10.7% |
| Shenzhen market cap | 2283.00 | 1,056.93 | 116.0% |
| Kweichou Moutai cap | 207272637 | 177697143.51 | 16.6% |
| Trading value (亿元) | 330.00 | 701.41 | 53.0% |
| "Waiting for response" | 8000 | 377,384 | 97.9% |

The agent's search tools return approximate values ("around $X", "near Y") that don't achieve the precision required for exact-match scoring. Without direct API access to real-time financial data feeds, these tasks are structurally difficult.

---

## 3. Third Failure Mode: Chinese Platform Data Inaccessible (13% of L3+L4 failures)

4 of 31 tasks fail specifically because the agent's web_search tool cannot retrieve ranking data from closed Chinese platforms:

| Task | Platform | Failure |
|------|----------|---------|
| Maoyan "Want to Watch" 6-8 | 猫眼 (Maoyan) | Retrieved wrong ranking positions |
| Dongchedi SUV hot list 3-5 | 懂车帝 (Dongchedi) | All 3 vehicles wrong |
| Dongchedi sedan hot list 2-4 | 懂车帝 (Dongchedi) | All 3 vehicles wrong; predicted 比亚迪/特斯拉, actual 奥迪A6L/速腾/迈腾 |
| Douban movies 2-4 | 豆瓣 (Douban) | Wrong movies entirely |

These platforms publish behind app interfaces or paywalled feeds that general web search cannot index. The agent finds peripherally related content (e.g., which films are in theaters) but cannot determine exact rank positions on the platform.

**However**: Chinese content is NOT the dominant cause of failure. The analysis below shows the breakdown:

---

## 4. Chinese Content: A Factor, Not the Primary Cause

### Distribution

| Level | Tasks with GT | Chinese-prompt | % Chinese |
|-------|-----:|------:|------:|
| L1 | 15 | 0 | 0% |
| L2 | 20 | 0 | 0% |
| L3 | 12 | 10 | 83% |
| L4 | 19 | 10 | 53% |

Chinese content is heavily concentrated in L3+L4 (65% of L3+L4 tasks), which is a real structural challenge.

### But the failure rates are similar

| Category | Total | Correct | Rate |
|----------|------:|--------:|-----:|
| L3+L4 Chinese-prompt | 20 | 0 | 0% |
| L3+L4 non-Chinese | 11 | 1 | 9.1% |

Chinese-prompt tasks do have a 0% success rate vs 9.1% for non-Chinese. But the non-Chinese rate is also catastrophically low — only 1 task (Box Office Mojo #1) was correct. The problem is not primarily that the tasks are Chinese, but that L3+L4 tasks require exact retrieval of specific data points that the agent's tools cannot reliably fetch in any language.

### Failure mode breakdown by language

| Failure Mode | Chinese | Non-Chinese | Total |
|-------------|--------:|------------:|------:|
| Agent gave up (hedged) | 7 | 4 | 11 |
| Numeric wrong (>5%) | 5 | 5 | 10 |
| Chinese platform inaccessible | 4 | 0 | 4 |
| Wrong data retrieved | 2 | 2 | 4 |
| Numeric near-miss (<5%) | 2 | 0 | 2 |
| **Total** | **20** | **11** | **31** |

The "agent gave up" and "numeric wrong" modes dominate both Chinese AND non-Chinese tasks equally. Chinese platform inaccessibility accounts for only 4/31 (13%) of failures.

---

## 5. Fourth Failure Mode: Wrong Data Retrieved (13% of L3+L4 failures)

4 tasks have confident but completely wrong predictions:

| Task | Predicted | Ground Truth | Issue |
|------|-----------|--------------|-------|
| PIF ATP singles 11-13 | Tommy Paul, Draper, Humbert | Muchova, Bencic, Noskova | Retrieved men's singles instead of women's doubles (or wrong ranking) |
| UK Singles 10-12 | Harry Styles songs | American Girls, Beauty And A Beat, Just the Way You Are | Wrong chart week or wrong positions |
| US TV programs 3-5 | 60 Minutes, The Equalizer, FBI | ABC World News, TBS NCAA Basketball, NBC Nightly News | Wrong week's data |
| Maoyan movies 6-8 | 真人快打2, 猪猪侠, 三心两意 | 流浪地球3, 杰克逊巨星之路, 我的妈耶 | Different date or ranking type |

These are temporal reasoning failures — the agent found valid-looking data but from the wrong date, wrong ranking type, or wrong category.

---

## 6. Structural Gap: Multiple-Choice vs Free-Form

| Level | Format | Example GT | Our Success |
|-------|--------|------------|------------:|
| L1 | Binary/MC (A, Yes/No) | `['A']`, `['Yes']` | 46.7% |
| L2 | Multi-select MC (A-N) | `['C', 'P']` | 45.0% |
| L3 | Free-form (ranked lists, exact values) | `['探岳', '宝马X3', 'RAV4荣放']` | 0.0% |
| L4 | Free-form (ranked lists, exact values) | `[1408.44]`, `['Project Hail Mary']` | 5.3% |

L1/L2 tasks constrain the answer space to explicit options listed in the prompt. L3/L4 tasks require the agent to produce the exact answer from scratch — specific names in specific order, or precise numeric values. The entire evolved skill/prompt/tool pipeline optimized for the constrained L1/L2 format.

---

## 7. The Single L4 Success

**Task**: "Which movie will be the latest #1 Release in Box Office Mojo's Domestic chart?"
**Prediction**: "Project Hail Mary"
**Ground Truth**: `['Project Hail Mary']`
**Score**: 1.0

This succeeded because: (1) single well-known item, (2) published on an English-language indexable site (Box Office Mojo), (3) widely reported in news, (4) exact name easily retrievable.

---

## 8. Comparison: H2O (Rank #3) Uses Same Model

H2O_AI_Super_Agent_v1.82 uses `claude_sonnet_4.6` and scores 53.21 overall:

| Level | A_EVOLVE_V2 | H2O | Gap |
|-------|------------:|----:|----:|
| L1 | 40.00 | 60.00 | -20.00 |
| L2 | 53.52 | 69.29 | -15.77 |
| L3 | 0.16 | 51.66 | -51.50 |
| L4 | 17.06 | 44.63 | -27.57 |

Same model, same knowledge cutoff. H2O likely has: direct API access to Chinese platforms (or cached feeds), real-time financial data APIs, and stricter answer formatting that meets exact-match requirements. The L3 gap (0.16 vs 51.66) is the strongest signal that our tool pipeline, not the model, is the bottleneck.

---

## 9. Root Cause Summary

| Root Cause | L3 Tasks | L4 Tasks | % of L3+L4 | Actionable? |
|-----------|:--------:|:--------:|:----------:|:-----------:|
| Agent gives up (hedged predictions) | 5 | 6 | 35% | Yes — force concrete answers |
| Numeric precision insufficient | 2 | 10 | 39% | Yes — add financial data APIs |
| Chinese platform data inaccessible | 4 | 0 | 13% | Yes — add platform-specific APIs |
| Wrong data retrieved (temporal errors) | 1 | 3 | 13% | Partially — improve date reasoning |
| Free-form format (structural) | All | All | 100% | Design — train/prompt for exact retrieval |

---

## 10. Recommendations (Prioritized by Impact)

### High Impact

1. **Force concrete answers, never hedge.** 35% of failures are the agent admitting defeat. Even a wrong concrete answer has a chance of being correct; a hedged non-answer always scores 0. Add a rule: "You MUST submit a specific answer. Never say 'unable to determine'."

2. **Add financial data APIs.** Yahoo Finance, Sina Finance (新浪财经), or Exchange Rate API for exact open/high/low/close/market-cap values. This alone could recover ~8 L4 tasks (the numeric ones). Web search returns approximate values that fail exact-match.

3. **Add Chinese platform scrapers or cached feeds.** Dongchedi (懂车帝), Maoyan (猫眼), Douban (豆瓣), KolRank, QQ Music, Maoer FM. These are closed platforms where general web search fails. This could recover ~4 L3 tasks.

### Medium Impact

4. **Improve temporal reasoning.** For "latest chart on date X" tasks, compute which edition is "latest" given publication schedules. Several failures retrieved the right data from the wrong date.

5. **Stop rounding numeric predictions.** The agent rounds (4,400 instead of 4,694.43). When the precise value cannot be found, search more specifically rather than approximating.

### Low Impact (Already Partially Addressed)

6. **Format enforcement.** Strip explanatory text from answers. Submit only the bare value/name.

7. **Don't hardcode data in evolved prompts.** The evolution process memorized approximate financial values that conflict with exact ground truth.
