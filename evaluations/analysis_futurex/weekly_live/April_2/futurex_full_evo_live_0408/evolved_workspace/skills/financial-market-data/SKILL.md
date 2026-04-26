---
name: financial-market-data
description: Look up stock prices, market indices, and financial data for temporal prediction tasks
---

# Financial Market Data Lookup Skill

## When to Use
- Task asks about stock prices (open, close, high, low) on a specific date
- Task asks about market index values (S&P 500, NASDAQ, Dow Jones, Nikkei)
- Task asks about whether a stock closed above/below a threshold
- Task asks about stock performance over a period
- Task asks about commodity prices (gold, crude oil)

## Strategy

### Step 1: Direct Price Search
- `"[index/stock] [date] close price"` or `"[index/stock] [date] open price"`
- `"[ticker] [month] [year] historical data"`
- `"[index] [date] final score"` (for indices)

### Step 2: Reliable Sources
- **StatMuse**: Good for historical stock/index data
- **Armstrong Economics Market Talk**: Daily market summaries
- **CNBC, WSJ, Bloomberg**: Market news with price data
- **Investing.com**: Historical OHLC data
- **Yahoo Finance**: Historical price data
- **Macrotrends**: Long-term historical price charts

### Step 3: For Intraday Data (Open/High/Low)
- Open price is often close to previous day's close
- For gap-down/gap-up events, search for news that caused the gap
- High/Low are harder to find exactly - look for intraday reports

### Step 4: "Above/Below Threshold" Questions
- Find the actual closing price first
- Compare to the threshold
- For multi-select "above $X" questions: if stock closed at $Y, all thresholds below $Y are correct

### Step 5: Reverse Stock Splits
- Always check if a stock had a reverse split before comparing historical prices
- Example: Opendoor (OPEN) did 1:20 reverse split on June 13, 2025
- Pre-split prices need to be multiplied by the split ratio for comparison

## Key Market Events (Jan 2026)
- **DeepSeek AI selloff (Jan 27, 2026)**: China's DeepSeek AI model news broke over weekend Jan 25-26, causing major selloff on Jan 27. NASDAQ fell 3.07%, Nvidia fell ~18% intraday.
- **S&P 500 all-time high (Jan 28, 2026)**: 7,002.28 (briefly surpassed 7,000)
- **Trump tariff relief (Jan 22, 2026)**: Trump backed off tariff threats on European countries over Greenland, causing DJIA to rise 1.2%
- **Gold record high (Jan 30, 2026)**: Hit intraday high ~$5,440 before massive crash to $4,713.90 spot close

## Key Data Points Observed (Jan 2026)
### Major Indices
- **DJIA Jan 22, 2026**: Closed at **49,077.23** (+1.2%, +588.64 pts)
- **S&P 500 Jan 23, 2026**: Closed at **6,915.61**
- **S&P 500 Jan 28, 2026**: Historical high of **7,002.28**
- **Nikkei 225 Jan 23, 2026**: Closed at **53,846.87** (+157.98 pts, +0.29%)
- **NASDAQ Jan 27, 2026**: Closed at **19,341.83** (-612.47 pts, -3.07%) - DeepSeek selloff

### Individual Stocks
- **PLTR Jan 31, 2026**: ~$145-146 (lost ~18% in January from $177.75 on Dec 31, 2025)
- **AAPL Jan 23, 2026**: Closed ~$247-248; 52-week high was $288.62 (Dec 3, 2025)
- **Li Auto (LI) Jan 20, 2026**: 52-week low of $15.71; Feb 4, 2026: ~$17.34
- **Tesla (TSLA) Jan 2026**: Range ~$430-458; never hit $400 or $500; closed $430.41 on Jan 30; Q4 2025 earnings beat Jan 28
- **Nvidia (NVDA) Jan 2026**: Range ~$178-192; never hit $170 or $200; closed $191.12 on Jan 30; lowest close $178.06 on Jan 20
- **Opendoor (OPEN) Jan 2026**: After 1:20 reverse split (Jun 13, 2025); was $7.29 on Jan 9, dropped to $5.76; hit $7, $6.50, $6, $5.50 but NOT $8.25+; Q4 2025 earnings beat (surged 16.5% after-hours)

### Commodities
- **Crude Oil (WTI/CL) Jan 2026**: Settled ~$65-70/barrel; week ending Jan 30 = $62.52/bbl (up 4.1% from $60.06); January high ~$62.52; Brent ~$70-72/barrel
- **Gold (GC) Jan 2026**: Hit intraday high ~$5,440 on Jan 30; April 2026 contract closed $5,121.20; spot closed $4,713.90 (massive crash); StatMuse reports Jan closing = $4,865.37; February 2026 contract (active month) ~$5,080


## Stock Data (March 2026)
- **NVDA March 9, 2026**: Closed at $182.64
- **NVDA March 16, 2026**: Closed at $183.22 (higher on March 16; driven by autonomous vehicle technology announcements)
- **S&P 500 March 13, 2026**: Hit 2026 low at 6,672.62 (third straight week of losses; oil near $100/barrel; weak jobs data)
- **S&P 500 March 6, 2026**: Down 1.3%; Nasdaq down 1.6%; Dow down ~450 points (weak jobs data, surging oil prices)
- **AAPL March 6 vs March 13, 2026**: Lower on March 13 (~$250.12 vs ~$255.92 on March 6)
- **TSLA March 2026**: Weekly losses of -13.7% as of March 6; continued market weakness
- **ORCL March 2026**: Oracle Q3 earnings (March 10, 2026 after bell) with revenue backlog up $30B; post-earnings jump pushed March 13 price above March 6 → YES (higher on March 13)
- **AMZN, GOOGL, MSFT March 2026**: All lower on March 13 than March 6 (broad market decline)

## Bitcoin (BTC) Data (Jan 2026)
- **Bitcoin Jan 2026**: Average closing price $90,463.82, down 10.2% for month
- **Bitcoin crashed to $77K** in January 2026 (39% drop from ATH ~$126K in Oct 2025)
- **Bitcoin Jan 31, 2026**: Closed at $78,336.15 (well below $100K)
- **Bitcoin below $82K in January 2026**: YES (crashed to $77K)
- Jim Cramer on Feb 1, 2026: confirmed Bitcoin had dropped below $80K
- Search: `"Bitcoin price January 2026 StatMuse"` for historical data


## Commodity Prices (Extended)
- **Soybeans Oct 2025 - Mar 2026**: Lowest closing price ~$9.65/bushel (option E: $9.50/bushel or more)
  - Search: `"soybean futures price [month year] historical data"`
  - CME Group, Barchart.com are reliable for commodity futures data

## "None of the Above" Handling
When a multi-select question asks "will X close above $Y?" and the actual price is BELOW all thresholds:
- The correct answer is to select NO options (empty selection)
- Use `\boxed{}` for empty selection if required
- Example: PLTR closed at ~$145 in Jan 2026, below all thresholds of $182-$206 → no options correct

## Gold Futures Active Month
- For Polymarket gold questions, "Active Month" = nearest delivery-cycle month (Feb, Apr, Jun, Aug, Oct, Dec)
- February 2026 contract was active month at end of January 2026
- April 2026 contract was the most actively traded but NOT the active month

## Golf Rankings (OWGR)
- Official World Golf Ranking (OWGR) updates weekly
- Search: `"OWGR week [N] [year] top 20 ranking"`
- Top players Jan 2026: #1 Scottie Scheffler, #2 Rory McIlroy
- Top 10 included: Schauffele, Rahm, Morikawa, Åberg, Fleetwood, Cantlay, Hovland, Matsuyama

## AI Benchmarks (METR)
- METR evaluates AI models on autonomous task completion
- "Time horizon" = 50% success rate on tasks of that duration
- GPT-5.2 (released Dec 11, 2025): METR time horizon = **6.6 hours** (6h 34min)
  - 95% CI: 3h 20min to 17h 30min
  - This is ≥4h, so option J in typical range questions
- Search: `"METR [model name] time horizon evaluation"`

## Tech Prices
- DDR5-6000 2x16GB RAM (Jan 2026): ~$400-500 range (option E in typical range questions)
  - Market experienced massive surge in late 2025 (163-619% increase)
  - Premium kits (Corsair Vengeance CL30 Black): ~$500-600
  - General market: ~$400-500

## Chinese A-Share Market Data (March 2026)
- **CanSino (SH:688185) March 20, 2026**: Intraday HIGH = **73.88 CNY**; closed at 71.76 CNY
- **CSI 300 Index March 23, 2026**: Down -3.26% from ¥4,567.02; approximately **~4,418 points** (4-week low)
- **CSI 300 Index March 31, 2026**: Closed at **4,450.05**
- **Ping An Bank (000001) Feb 27, 2026**: Stock price ¥10.90; market cap = **2,115.25 亿元** (194.06 亿股 outstanding)
- **Agricultural Bank of China (601288) March 23, 2026**: A-share market cap ≈ **178,491,330 万元** (~1.78 trillion yuan)
- **India Market Fund LOF (SZ:164824)**: Feb 5, 2026 = ¥1.4220; Mar 6, 2026 = ¥1.35; Mar 19, 2026 ≈ ¥1.38

## Chinese A-Share Market Cap Calculation
- Market cap = shares_outstanding × stock_price
- **Ping An Bank (000001)**: 19,405,918,198 shares outstanding (as of Dec 31, 2025)
- **Agricultural Bank of China (601288)**: ~349,983 million A-shares outstanding
- For stock high/low on specific dates: Search "[stock code] [date] 盘中最高价" or "[stock] [date] high"
- For market cap: Search "[stock code] [date] 总市值" on Sina Finance, Eastmoney, or similar

## China Coastal Bulk Freight Index (CBFI) - 中国沿海散货运价指数
- Published by Ministry of Transport (交通运输部)
- **Feb 27, 2026**: Product Oil (成品油) freight index = **1379.39 points** (down 3.4% from Jan 2026 end)
- **March 20, 2026**: Composite Index = **1142.47** (up 9.9% from March 13); Coastal Dry Bulk Index = **1102.96** (up 11.9%); Coal Index = **1181.63**
- Search: "中国沿海散货运价指数 [date]" or "CBFI [date]"
