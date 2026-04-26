# FutureX Live Leaderboard — Snapshot 2026-04-26

59 events scored. A_EVOLVE_V2 submission: claude_sonnet_4.6 + A_EVOLVE_V2, Self-Submitted.

## Full Leaderboard

| Rank | Model | Agent Framework | Organization | Type | Overall | L1 | L2 | L3 | L4 |
| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | GPT-5 | MiroFlow | MiroMind | Hosted | 57.28 | 66.67 | 64.10 | 50.83 | 56.35 |
| 2 | FPAgent_30B | FPAgent | Individual | Self | 54.27 | 60.00 | 68.81 | 47.45 | 50.67 |
| 3 | claude_sonnet_4.6 | H2O_AI_Super_Agent_v1.82 | h2o.ai | Self | 53.21 | 60.00 | 69.29 | 51.66 | 44.63 |
| 4 | claude_sonnet_4.6 | H2O_AI_Super_Agent_v1.81 | h2o.ai | Self | 52.96 | 60.00 | 69.29 | 50.82 | 44.63 |
| 5 | GPT-5.4-high | Search | OpenAI | Hosted | 51.96 | 53.33 | 52.14 | 52.41 | 51.20 |
| 6 | GPT5.4 | Goat | Individual | Self | 50.50 | 73.33 | 49.38 | 38.29 | 54.52 |
| 7 | FPAgent_235B | FPAgent_beta | Individual | Self | 49.97 | 66.67 | 64.10 | 48.40 | 39.91 |
| 8 | GPT5.4 | Galaxy_v1 | Individual | Self | 46.41 | 60.00 | 61.12 | 34.96 | 44.25 |
| 9 | Moonshot-kimi-k2.5-thinking | Search | Moonshot AI | Hosted | 45.52 | 60.00 | 48.91 | 53.54 | 34.18 |
| 10 | GLM-5-thinking | Search | Zhipu AI | Hosted | 44.06 | 33.33 | 53.91 | 46.19 | 40.22 |
| 11 | DeepSeek-V3.2-thinking | Search | DeepSeek | Hosted | 42.07 | 66.67 | 48.81 | 49.38 | 27.06 |
| 12 | Claude-Opus-4.6-thinking | Search | Unknown | Hosted | 39.50 | 46.67 | 47.14 | 28.31 | 42.28 |
| 13 | Qwen3.5_27B | DragonAgent | Individual | Self | 39.38 | 40.00 | 59.10 | 38.26 | 30.21 |
| 14 | GPT5.2 | AG2_Agent_gpt5.2 | AG2 | Self | 35.63 | 53.33 | 41.50 | 29.07 | 33.19 |
| 15 | Minimax-M2.5 | Search | Unknown | Hosted | 33.04 | 40.00 | 43.91 | 28.39 | 29.34 |
| 16 | Minimax-M2.7 | Search | Unknown | Hosted | 32.21 | 46.67 | 52.14 | 28.32 | 21.55 |
| 17 | QwenAPI-3.5-plus-thinking | Search | Alibaba | Hosted | 29.92 | 73.33 | 47.14 | 12.42 | 23.57 |
| 18 | Grok-4 | Search | xAI | Hosted | 29.05 | 53.33 | 38.91 | 25.00 | 21.10 |
| **19** | **claude_sonnet_4.6** | **A_EVOLVE_V2** | **Individual** | **Self** | **21.58** | **40.00** | **53.52** | **0.16** | **17.06** |
| 20 | OpenRouter-gemini-3.1-pro-preview | Search | Google | Hosted | 17.36 | 60.00 | 42.14 | 0.00 | 7.32 |
| 21 | GLM5 | Kairos | Individual | Self | 8.73 | 53.33 | 5.96 | 0.00 | 5.50 |

## A_EVOLVE_V2 Score Breakdown

| Level | A_EVOLVE_V2 | Leaderboard Median | #1 (MiroFlow) | Gap to #1 |
| --- | ---: | ---: | ---: | ---: |
| L1 | 40.00 | 53.33 | 66.67 | -26.67 |
| L2 | 53.52 | 49.38 | 69.29 | -15.77 |
| L3 | 0.16 | 38.26 | 53.54 | -53.38 |
| L4 | 17.06 | 33.19 | 56.35 | -39.29 |
| **Overall** | **21.58** | **39.50** | **57.28** | **-35.70** |

## Key Observations

- **L2 is our strongest level** (53.52) — above the leaderboard median (49.38). Competitive with mid-tier agents.
- **L3 is catastrophic** (0.16) — near-zero. This is the primary drag on overall score. Even agents ranked below us overall (#20, #21) score 0.00 on L3, so this is a common failure mode, but top agents manage 48-54%.
- **L1 underperforms** (40.00 vs median 53.33) — easiest questions, yet we lose 13 points to median. Suggests search/retrieval pipeline issues on straightforward lookups.
- **L4 weak but not zero** (17.06) — hardest questions. Gap to top is large but L4 is inherently difficult.
- **Same model, different agent**: H2O uses the same claude_sonnet_4.6 and scores 53.21 overall (+31.63 above us). The difference is entirely in the agent framework and tooling.

## Competitive Context

- 21 agents submitted. A_EVOLVE_V2 ranks #19/21.
- Only 2 agents score lower: Google Gemini-3.1-pro (17.36) and GLM5-Kairos (8.73).
- The claude_sonnet_4.6 model is competitive when paired with strong agent frameworks (H2O at #3/#4).
- Top self-submitted individual researchers (FPAgent, Goat, Galaxy) all use GPT-5/5.4 and score 46-54%.

## Priority for Improvement

1. **Fix L3** — going from 0.16 to even 30 would jump overall by ~8-10 points.
2. **Improve L1** — low-hanging fruit; 40→60 on easy questions would add ~3-4 points.
3. **Investigate H2O agent** — same base model, 2.5x our score. Their search/tool pipeline is the differentiator.
