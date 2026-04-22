# PolyBench Domain Profile

> Phase 1 of the research skill: understand the benchmark before running experiments.

## 1. What Is PolyBench?

PolyBench is a backtesting benchmark for prediction-market trading agents.
Each **task** is a frozen snapshot of a real Polymarket event taken *before* it
resolved.  The agent sees the market question, order book, prices, and news
articles, then decides whether to trade.  After all predictions are collected,
they are scored against the actual resolution.

The benchmark tests a blend of:
- **Information synthesis** (news articles, event descriptions, resolution rules)
- **Probabilistic reasoning** (Bayesian estimation vs. market-implied probability)
- **Calibration** (does the agent's confidence track its accuracy?)
- **Risk management** (knowing when *not* to trade)

Source DB: `data/polymarket_analysis.db`

---

## 2. Database Schema

```
events          -- 4,997 events (parent containers)
  id, title, description, tags, start_date, end_date, total_volume

markets         -- 38,666 markets (one per tradeable question)
  id, event_id, question, description, outcomes (JSON), outcome_prices (JSON),
  volume, liquidity, end_date

market_snapshots -- 38,666 snapshots (order book + news at scrape time)
  id, market_id, event_id, timestamp, news_context, order_book_snapshot,
  market_prices, ready_for_analysis

resolutions     -- 11,879 resolved markets
  id, market_id, winning_outcome, resolution_source, resolved_at
```

Key relationships: each market belongs to one event; each snapshot captures one
market at one point in time; each resolution records the final outcome.

---

## 3. Filtering Funnel

Not all 11,879 resolved markets are usable.  Dead and degenerate markets waste
agent time with guaranteed SKIPs.

| Stage | Count | Notes |
|---|---|---|
| All markets | 38,666 | |
| Resolved + ready | 11,879 | Have a `winning_outcome` and `ready_for_analysis = 1` |
| Has order book (len > 5) | 5,097 | 57% had empty/null OBs |
| Not degenerate prices | **5,075** | Exclude `["0","1"]`, `["1","0"]`, `[]` |

The 6,782 rejected markets fall into two groups:
- **Empty OBs** (~6,780): the market had already resolved or been delisted before
  the snapshot scrape; no order book was available.
- **Post-resolution prices** (~22): prices stuck at 0/1 from after resolution;
  the market is already settled, nothing to trade.

The SQL filter in `polybench.py`:
```sql
WHERE ms.ready_for_analysis = 1
  AND LENGTH(ms.order_book_snapshot) > 5
  AND m.outcome_prices NOT IN ('["0", "1"]', '["1", "0"]', '[]')
ORDER BY r.resolved_at, ms.timestamp
```

---

## 4. Task Characteristics

### 4.1 Price Distribution (YES price at snapshot)

How uncertain are the markets the agent faces?

| YES Price Bucket | Count | % | Interpretation |
|---|---|---|---|
| 0.00 - 0.05 | 1,161 | 22.9% | Near-certain NO; no edge unless contrarian |
| 0.05 - 0.10 | 206 | 4.1% | Strong NO lean |
| 0.10 - 0.20 | 335 | 6.6% | Moderate NO lean |
| 0.20 - 0.30 | 416 | 8.2% | Slight NO lean |
| 0.30 - 0.40 | 421 | 8.3% | Competitive |
| 0.40 - 0.50 | 600 | 11.8% | Near coin-flip |
| 0.50 - 0.60 | 1,338 | 26.4% | Near coin-flip / slight YES lean |
| 0.60 - 0.70 | 187 | 3.7% | Slight YES lean |
| 0.70 - 0.80 | 148 | 2.9% | Moderate YES lean |
| 0.80 - 0.90 | 109 | 2.1% | Strong YES lean |
| 0.90 - 0.95 | 50 | 1.0% | Near-certain YES |
| 0.95 - 1.00 | 104 | 2.0% | Near-certain YES |

**Key insight**: ~47% of tasks have prices between 0.30 and 0.60 (genuinely
uncertain).  ~27% are near-certain (< 0.05 or > 0.95).  The agent's primary
skill test is in the 0.10-0.90 range where there's room for mispricing.

### 4.2 Outcome Types

| Type | Count | % |
|---|---|---|
| Binary (Yes/No) | 3,450 | 68.0% |
| Multi-outcome (named) | 1,625 | 32.0% |

Binary markets have outcomes `["Yes", "No"]`.  Multi-outcome markets have team
names, over/under, or other labels:
- `["Seahawks", "Patriots"]` -- sports spread/winner
- `["Over", "Under"]` -- totals
- `["Up", "Down"]` -- crypto price direction
- `["Knicks", "Celtics"]` -- head-to-head

The agent must output the **exact winning outcome string** (case-insensitive
match).  For binary markets, `side = "YES"` or `"NO"`.  For multi-outcome
markets, `side = "SEAHAWKS"`, `"UNDER"`, etc.

### 4.3 Winning Outcome Bias

Among binary (Yes/No) markets:

| YES Price Bucket | Total | YES Wins | YES Win % | Market Calibration |
|---|---|---|---|---|
| < 0.10 | 1,318 | 16 | 1.2% | Well-calibrated (price ~5%) |
| 0.10 - 0.30 | 617 | 101 | 16.4% | Well-calibrated (price ~20%) |
| 0.30 - 0.50 | 779 | 266 | 34.1% | Slightly low (price ~40%) |
| 0.50 - 0.70 | 445 | 267 | 60.0% | Well-calibrated (price ~60%) |
| 0.70 - 0.90 | 171 | 144 | 84.2% | Well-calibrated (price ~80%) |
| >= 0.90 | 120 | 120 | 100.0% | Fully calibrated |

**Key insight**: Polymarket is well-calibrated overall.  The 0.30-0.50 bucket
shows a slight negative bias (YES wins 34% when priced at ~40%).  An agent that
simply trusts market prices and only trades on strong evidence will have a hard
time beating the market consistently.  The edge, if any, comes from:
1. News interpretation the market hasn't priced in
2. Resolution rule nuances (e.g., 50-50 split clauses, date conditions)
3. Multi-outcome markets where the OB is thinner and less efficient

### 4.4 Overall Outcome Distribution (all filtered markets)

| Winning Outcome | Count |
|---|---|
| No | 2,536 |
| Yes | 914 |
| Under | 537 |
| Over | 463 |
| (named teams/entities) | ~625 |

Strong NO dominance: 2,536 vs 914.  A naive "always BUY NO" agent with
confidence 0.7 would achieve ~50% accuracy on the full dataset.

### 4.5 News Context Availability

| Quality | Count | % |
|---|---|---|
| No news | 870 | 17.1% |
| Minimal (< 500 chars) | 26 | 0.5% |
| Some (500-2K chars) | 83 | 1.6% |
| Good (2K-5K chars) | 930 | 18.3% |
| Rich (> 5K chars) | 3,166 | 62.4% |

~83% of tasks have meaningful news context.  The 17% with no news are harder --
the agent must rely on the question text, resolution rules, and OB data alone.

### 4.6 Order Book Spread

Among binary (Yes/No) markets with spread data:

| Spread | Count | % | Meaning |
|---|---|---|---|
| < 1% | 735 | 21.3% | Very tight; efficient market, hard to find edge |
| 1-3% | 983 | 28.5% | Tight; small edge possible |
| 3-5% | 446 | 12.9% | Moderate; reasonable opportunity |
| 5-10% | 343 | 9.9% | Wide; likely edge exists |
| >= 10% | 510 | 14.8% | Very wide; thin market, edge likely but execution risk |

~25% of markets have spreads >= 5%, making them the most promising trading
targets.  The agent should factor spread width into its edge calculation.

### 4.7 Trading Volume

| Volume | Count | % |
|---|---|---|
| < $1K | 3,147 | 62.0% |
| $1K - $10K | 980 | 19.3% |
| $10K - $100K | 680 | 13.4% |
| $100K - $1M | 224 | 4.4% |
| >= $1M | 44 | 0.9% |

Most markets are low-volume.  High-volume markets (> $100K) tend to be more
efficient -- less edge.  The sweet spot for alpha is likely $1K-$100K volume
where there's enough participation to provide information but not so much that
the market is perfectly priced.

### 4.8 Time to Resolution

| Horizon | Count | % |
|---|---|---|
| < 12 hours | 571 | 11.3% |
| 12h - 1 day | 272 | 5.4% |
| 1 - 3 days | 1,968 | 38.8% |
| 3 - 7 days | 1,780 | 35.1% |
| 7 - 10 days | 320 | 6.3% |
| 10 - 15 days | 164 | 3.2% |

- **Min**: ~0 days (resolves within hours of snapshot)
- **Median**: 2.75 days
- **Mean**: 3.35 days
- **Max**: 14.6 days

All snapshots were taken Feb 6-12, 2026 (batch scrape).  Resolutions span
Feb 6-21, 2026.  Short-horizon tasks (< 12h) are close to resolution and often
have near-certain prices; these are the "already decided" markets.  The bulk
(74%) resolve within 1-7 days -- the primary reasoning challenge.

Note: time-to-resolution directly impacts APY calculation:
`APY = raw_return * (365 / days_held)`.  A +50% return on a 1-day trade
annualizes to +18,250%, making APY very noisy for short-horizon tasks.

---

## 5. Task Input Format

The benchmark adapter (`polybench.py:_format_input`) assembles a text prompt
from each DB row.  The agent sees:

```
Current Date: 2026-02-06 15:14:37
Event: Will the New England Patriots win Super Bowl 2026?
Description & Rules: <official resolution rules>

=== MARKET OPTIONS WITH HISTORICAL ORDER BOOK DATA ===

## Option ID: 540227
Question: Will the New England Patriots win Super Bowl 2026?
Last Known Prices: ["0.3175", "0.6825"]

Historical Order Book Analysis:
Outcome: Yes
  - Best Bid: 0.3170, Best Ask: 0.3190
  - Spread: 0.0020 (0.20%)
  - Mid Price (implied probability): 0.3180
  - Bid liquidity (top 3): $48,314.70
  - Ask liquidity (top 3): $78,469.92
Outcome: No
  - Best Bid: 0.6810, Best Ask: 0.6830
  ...
Final Trading Volume: $15,736,424.15
Liquidity: $...

=== EVIDENCE & CONTEXT AT SNAPSHOT TIME ===
--- News Article 1 ---
<headline + body>
--- News Article 2 ---
<headline + body>

TASK:
Analyze the historical evidence AND historical order book data.
Identify ALL options that are mispriced.
The stated prices imply probabilities. Order book mid-prices show actual market state.
Signal a trade for ANY option where your estimated probability
differs significantly from price.
```

**What the agent does NOT see**: the winning outcome, the resolution date, or
any evaluation scores.  It must reason from evidence alone.

---

## 6. Agent Architecture

The PolyBench agent uses the strands SDK with two tools:

1. **`sequentialthinking`** -- structured chain-of-thought reasoning
2. **`submit`** -- final prediction output

The system prompt (`experiments/polybench/seed/prompts/system.md`) instructs
Bayesian reasoning:
1. Read event description and resolution rules
2. Analyze order book: spreads, depth, mid-price vs stated probability
3. Evaluate news evidence for/against each outcome
4. Estimate true probability using Bayesian reasoning
5. Compare estimate to market price -- is there edge?
6. If edge, submit; otherwise SKIP

---

## 7. Expected Agent Output

The agent calls `submit` with a JSON prediction:

```json
{
  "decision": "BUY",
  "side": "NO",
  "confidence": 0.75,
  "reasoning": "Patriots are priced at 31.75% to win but...",
  "est_resolution_date": "2026-02-09"
}
```

Fields:
- **`decision`**: `BUY` (go long on `side`), `SELL` (go short), or `SKIP`
- **`side`**: the outcome to trade -- `YES`, `NO`, or a named outcome
- **`confidence`**: 0.0 to 1.0; below 0.6 is treated as SKIP
- **`reasoning`**: free-text justification (not scored)

---

## 8. Evaluation Pipeline

### 8.1 Step-by-step walkthrough

Using the Patriots Super Bowl example (market 540227):

**Step 1 -- Parse output**:
```
decision = "BUY", side = "NO", confidence = 0.75
```

**Step 2 -- Confidence gate**:
```
0.75 >= 0.6  -->  passes (if < 0.6, treated as SKIP, score = 0)
```

**Step 3 -- Skip check**:
```
decision != "SKIP" and side != ""  -->  continues
```

**Step 4 -- Correctness**:
```
winning_outcome = "No"   (normalized -> "NO")
side            = "NO"
decision        = "BUY"

Rule:  BUY  -> correct if (winning == side)
       SELL -> correct if (winning != side)

Result: "NO" == "NO" -> correct
```

**Step 5 -- Trade simulation** (two parallel fills):

*Unit trade* (flat $10 budget):
```
Walk the NO ask book:
  best ask = $0.683, plenty of liquidity
  Buy: $10.00 / $0.683 = 14.64 shares

Correct -> profit = shares * $1.00 - spent = 14.64 - 10.00 = +$4.64
Wrong   -> profit = -spent = -$10.00

raw_return = +4.64 / 10.00 = +46.4%
```

*CWR trade* (confidence-weighted: $10 * 0.75 = $7.50 budget):
```
Buy: $7.50 / $0.683 = 10.98 shares
Correct -> profit = 10.98 - 7.50 = +$3.48
```

**Step 6 -- APY**:
```
snapshot  = 2026-02-06 15:14
resolved  = 2026-02-09 07:20
days_held = max(1, 3) = 3

APY = raw_return * (365 / days_held) = 0.464 * 121.67 = +56.5x annualized
```
(Extreme because of the short 3-day hold.  APY is noisy for short horizons.)

### 8.2 Feedback object

```python
Feedback(
    success = True,
    score   = 1.0,       # accuracy: binary 1 or 0
    detail  = "Correct: BUY NO (conf=0.75), winning=No, return=+46.4%, cwr=+3.48",
    raw     = {
        "decision": "BUY",  "side": "NO",  "confidence": 0.75,
        "winning_outcome": "No",  "is_correct": True,
        "unit_investment": 10.0,  "unit_profit": 4.64,
        "raw_return": 0.464,
        "cwr_investment": 7.50,  "cwr_profit": 3.48,
        "apy": 56.5,
    },
)
```

### 8.3 Wrong prediction example

Same market, agent says `BUY YES` (confidence 0.8):
```
winning = "NO", side = "YES" -> "NO" != "YES" -> incorrect

Unit trade: spent $10, bought 31.35 YES shares at $0.319
Shares are worthless (YES didn't win) -> profit = -$10.00
raw_return = -100%

Feedback: score=0.0, success=False
```

### 8.4 Confidence gate example

Agent says `BUY NO` (confidence 0.55):
```
0.55 < 0.6  ->  gated out, treated as SKIP
Feedback: score=0.0, gated=True
```
This prediction is excluded from all aggregate metrics.

---

## 9. Aggregate Metrics (Official PolyBench)

Per-task evaluation produces binary accuracy + financial metrics.  At analysis
time, these are aggregated into the official PolyBench metric suite:

| Metric | Formula | What It Measures |
|---|---|---|
| **Accuracy** | `correct / total_traded` | Raw prediction quality |
| **F1** | `2*P*R / (P+R)` where positive = BUY | Balance of precision and recall on trades |
| **ECE** | `sum(bin_weight * |avg_conf - avg_acc|)` | Calibration: does 70% conf = 70% accuracy? |
| **Non-CWR Return** | `mean(raw_returns)` | Average return per flat-$10 trade |
| **CWR Return** | `sum(cwr_profits) / sum(cwr_investments)` | Portfolio return with confidence sizing |
| **APY** | `mean(raw_return * 365/days)` | Annualized return (noisy, short horizons) |
| **Sharpe** | `mean(APYs) / std(APYs)` | Risk-adjusted return |

The confidence gate at 0.6 means only high-conviction trades enter these
calculations.  An agent that SKIPs 90% of tasks but nails the 10% it trades
will score better than one that trades everything at low confidence.

---

## 10. What Makes This Benchmark Hard

### 10.1 Markets are well-calibrated

The Polymarket calibration table (Section 4.3) shows that market prices track
actual outcomes closely.  There is no systematic mispricing to exploit.  The
agent must find *individual* mispricings via news interpretation or rule
analysis, not broad statistical patterns.

### 10.2 Most tasks are uninteresting

~23% of tasks have YES prices < 5% (near-certain NO).  The correct action is
almost always SKIP.  But if the agent blindly trades these, it can get lucky
(1.2% YES win rate means 1-in-83 contrarian bets would pay off at ~20:1).
The expected value of trading near-certain markets is ~zero, but variance is
high.

### 10.3 Edge requires domain knowledge

Sports outcomes need team strength assessment.  Crypto price targets need
recent price trajectory.  Political markets need polling data.  The news
articles provide *some* of this context, but 17% of tasks have no news at all.

### 10.4 Multi-outcome markets are tricky

32% of tasks have named outcomes.  The agent must output the exact string
(e.g., `"FURIA"` not `"FURIA Esports"`).  The OB structure is also different --
each named outcome has its own Yes/No book within the market.

### 10.5 APY is extremely noisy

With a median hold of 2.75 days, APY amplifies returns by ~130x.  A +5% return
becomes +660% APY.  A -5% loss becomes -660% APY.  Sharpe ratio attempts to
adjust for this, but with such extreme values, it's dominated by outliers.

### 10.6 The confidence gate is a double-edged sword

Setting confidence >= 0.6 means the agent must be decisive.  "I think NO is
slightly more likely" (conf 0.55) doesn't count.  But being too confident on
wrong predictions is maximally punished (full -$10 loss).  The optimal strategy
balances selectivity (high skip rate) with conviction (high confidence on
trades).

---

## 11. Baseline Strategies and Expected Performance

| Strategy | Expected Accuracy | Expected CWR | Notes |
|---|---|---|---|
| Always SKIP | N/A (no trades) | 0% | No risk, no reward |
| Always BUY NO (conf 0.7) | ~50% on binary | Negative | NO wins 73% overall but agent also hits multi-outcome |
| Trust market + small edge | ~55-65% | Small positive | Trade only when confident, agree with market direction |
| Perfect oracle | 100% | Very high | Upper bound; unreachable |

Our test-DB baseline run achieved **58.9% accuracy** (53/90 passed) on a
60-market test database.  This establishes the starting point for evolution
experiments.

---

## 12. Pipeline Data Flow Summary

```
                          DATABASE
                             |
                    polybench.py:get_tasks()
                             |
                    [Task(id, input, metadata)]
                             |
                     metadata includes:
                     - winning_outcome (hidden from agent)
                     - order_book_snapshot (for evaluation)
                     - outcome_prices (for fallback pricing)
                     - resolved_at (for APY calculation)
                             |
              +--------------+--------------+
              |                             |
        task.input                    task.metadata
        (agent sees)                  (evaluator sees)
              |                             |
        Agent reasons                       |
        via strands SDK                     |
              |                             |
        trajectory.output                   |
        (JSON prediction)                   |
              |                             |
              +---------> evaluate() <------+
                             |
                    Feedback(success, score, detail, raw)
                             |
              +--------------+--------------+
              |              |              |
         Orchestrator    Observer       Analysis
         history.jsonl   batch_*.jsonl  analyze_all.py
         (outside ws)    (in ws, gated) (post-hoc)
```

With `--trajectory-only`: Observer batch files exclude `success`, `score`, and
`feedback_detail`.  The evolver can see *what* the agent predicted and *how* it
reasoned, but not *whether* it was right.  This forces evolution to improve
reasoning quality rather than overfit to outcomes.
