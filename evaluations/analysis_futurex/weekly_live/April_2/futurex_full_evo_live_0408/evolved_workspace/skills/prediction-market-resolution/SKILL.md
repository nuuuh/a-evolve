---
name: prediction-market-resolution
description: Find resolution data from prediction markets (Manifold, Polymarket, Metaculus) to inform temporal predictions
---

# Prediction Market Resolution Skill

## When to Use
- Task references a Manifold Markets, Polymarket, or Metaculus question
- Task is about niche events that may have prediction market coverage
- You need to cross-check your prediction against market consensus
- Direct factual sources are hard to find

## Strategy

### Step 1: Search for Market Resolution
- `"Manifold [event description] resolved"`
- `"[event] Manifold Markets [year] resolution"`
- `"site:manifold.markets [event keywords]"`

### Step 2: Interpret Market Data
- **100% or 99%+ for an option**: Very strong evidence that option resolved YES
- **Market "resolved Jan 14"**: The market has been officially resolved
- **"Resolved YES/NO"**: Binary market outcome
- **"Resolved MKT"**: Multiple-choice market with specific options resolved

### Step 3: Cross-Reference
- Verify market resolution against primary sources when possible
- Market resolution data is generally reliable but check for edge cases

## Key Patterns Observed
- Manifold "Guessing Game" pages show aggregated market probabilities
- Search snippet format: "100.0%. [Option Name]" means that option resolved YES
- "resolved Jan 14" in snippet indicates resolution date
- Market creator updates (AI summaries) provide context about resolution criteria

## Manifold-Specific Tips
- Search `"manifold.markets [market title]"` for direct market pages
- The "Guessing Game" aggregator page shows multiple related markets
- Creator updates often clarify resolution criteria for ambiguous cases
- Multiple-choice markets can have multiple options resolve YES

## Example Searches
- `"Manifold Global Average Temperature Dec 2025 LOTI resolved"`
- `"manifold bens puzzle round 2 winner resolved"`
- `"site:manifold.markets who will post winning guess bens puzzle"`

## Niche Personal Markets (Tetraspace, etc.)
When a market is about a specific person's personal life (location, activities):
- Search `"[person name] [date] [location/activity]"` directly
- Check the person's social media or blog for clues
- If resolution cannot be found, consider the "Other" option as a fallback
- These markets are often very hard to resolve without direct access to the market page

## ClaudePlaysPokemon Markets
- The Opus 4.5 run was active in late 2025/early 2026
- Safari Zone costs $500 per attempt, 500 steps per attempt
- Minimum steps: ~270 for Gold Teeth, ~399 for Secret House (HM Surf)
- The 4.6 run had $22,257 before Safari Zone
- Community noted Safari Zone is "near impossible" for AI to clear before running out of money
- Market update: "Will not resolve to 'Does not complete' immediately if Claude runs out of money"

## Caution
- Market prices before resolution are probabilistic, not definitive
- Only treat as definitive when market shows "resolved" status
- High probability (e.g., 99%) before resolution is strong but not certain
- For niche personal markets, if you can't find the resolution, make your best educated guess
