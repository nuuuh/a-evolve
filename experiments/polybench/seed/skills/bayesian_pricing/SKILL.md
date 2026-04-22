---
name: bayesian_pricing
description: Estimate true probability using Bayesian reasoning on prediction market evidence
trigger: When analyzing a prediction market with news context and order book data
---

## Bayesian Pricing Skill

When evaluating a prediction market:

1. **Base rate**: Start from the market mid-price as the prior probability
2. **Evidence update**: For each piece of news/evidence, estimate the likelihood ratio
   - Strong direct evidence (official announcement, ruling): shift 20-40%
   - Moderate evidence (credible report, polling): shift 10-20%
   - Weak/indirect evidence (rumor, opinion): shift 5-10%
3. **Order book signal**: Compare mid-price to your posterior
   - Wide spread (>10%) = high uncertainty, be cautious
   - Narrow spread with depth = strong consensus
   - Bid/ask imbalance may indicate informed trading
4. **Edge threshold**: Only trade if |your_estimate - mid_price| > spread + 0.05
5. **Confidence calibration**:
   - 0.6-0.7: mild edge, moderate evidence
   - 0.7-0.85: clear edge, strong evidence
   - 0.85+: requires direct quotes/stats from context (Rule 3)
