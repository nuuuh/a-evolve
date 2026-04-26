---
name: economic-data-lookup
description: Look up official economic statistics (inflation, unemployment, GDP, interest rates) for temporal prediction tasks
---

# Economic Data Lookup Skill

## When to Use
- Task asks about inflation rates (CPI, HICP)
- Task asks about unemployment rates
- Task asks about GDP, trade data, or other economic indicators
- Task asks about central bank interest rate decisions
- Resolution date aligns with official data release dates

## Strategy

### Step 1: Identify the Data Source
- **Canada CPI**: Statistics Canada (StatsCan), released ~3 weeks after reference month
- **UK Unemployment**: ONS Labour Market Overview, released monthly
- **Eurozone Inflation**: Eurostat flash estimate (end of reference month), final (~3 weeks later)
- **US CPI**: Bureau of Labor Statistics (BLS)
- **NASA GISTEMP**: Released ~mid-month for previous month
- **Bank of Japan (BOJ)**: Policy meetings ~8x/year; minutes published ~1 month later
- **Bank of Brazil (COPOM)**: Policy meetings ~8x/year
- **Bank of England (BOE)**: Policy meetings ~8x/year
- **Reserve Bank of Australia (RBA)**: Policy meetings ~8x/year

### Step 2: Search for Official Release
- `"[country] [indicator] [month year] [official agency]"`
- `"[country] CPI [month year] year-over-year"`
- `"[central bank] rate decision [month year]"`
- Include the release date in search if known

### Step 3: Baseline Conversion
- Different agencies use different baselines
- NASA GISTEMP uses 1951-1980 baseline
- NOAA uses 20th century average (1901-2000)
- Eurostat uses HICP methodology
- Always check which baseline the question specifies

## Key Data Points Observed
- **Canada Dec 2024 CPI**: 1.8% YoY (GST/HST holiday effect)
- **UK Sep-Nov 2025 Unemployment**: 5.1% (ONS Jan 20, 2026 release)
- **Eurozone Dec 2024 Inflation**: 2.4% (Eurostat flash Jan 7, 2025)
- **NASA GISTEMP Dec 2025**: <1.095°C vs 1951-1980 baseline
- **Bank of Japan (Dec 19, 2025)**: Raised rate +0.25pp to **0.75%**
- **Bank of Japan (Jan 22-23, 2026)**: Held rate unchanged at **0.75%** (8-1 vote)
- **Bank of Brazil COPOM (Jan 27-28, 2026)**: Held Selic rate unchanged at **15.00%** (5th consecutive hold, highest since July 2006)
- **Reserve Bank of Australia (Feb 3, 2026)**: **RAISED** cash rate +25bps to **3.85%** (surprise hike; first increase since Nov 2023; ended short rate-cutting cycle)
- **ECB (European Central Bank) Feb 5, 2026**: Held deposit facility rate UNCHANGED at **2.00%** (same as Dec 18, 2025)
- **US January 2026 Jobs Report**: Added **130,000** nonfarm payroll jobs (beat ~55,000 consensus; strongest monthly gain in over a year; falls in "more than 125k" category)
- **China CPI February 2026**: 1.3% YoY (up from 0.2% in January 2026; highest since January 2023; driven by Lunar New Year holiday spending; greater than 0.2% = YES)
- **Brazil IPCA February 2026**: 0.70% monthly inflation (above 0.45% threshold; beat expectations of 0.49%)
- **US PCE January 2026**: 2.8% annual inflation (NOT greater than 2.9%; eased from December 2025's near two-year high of 2.9%)
- **Reserve Bank of Australia (Mar 2026)**: **RAISED** cash rate +25bps to **4.10%** (second consecutive hike; 5-4 split vote; citing renewed inflation pressures and stronger economic momentum)

## Reliable Sources
- Statistics Canada: statcan.gc.ca
- ONS: ons.gov.uk
- Eurostat: ec.europa.eu/eurostat
- NASA GISS: data.giss.nasa.gov
- NOAA: ncei.noaa.gov
- Bank of Japan: boj.or.jp
- Banco Central do Brasil: bcb.gov.br
- Reserve Bank of Australia: rba.gov.au
- FocusEconomics: focuseconomics.com (good for central bank summaries)

## Prediction Market Cross-Check
- Search Manifold Markets for the same question to find resolution data
- Example: `"Manifold [indicator] [month year] resolved"` 
- Market resolution at 99%+ for an option is strong evidence

## Baseline Conversion Notes
- NASA GISTEMP (1951-1980) vs NOAA (1901-2000): GISTEMP anomalies are ~0.1-0.15°C LOWER
- If NOAA reports 1.05°C above 20th century avg, GISTEMP would show ~0.90-0.95°C

## Central Bank Rate Decision Strategy
1. Search `"[bank name] rate decision [month year] result"`
2. Check if the meeting date is before or after the resolution date
3. For "same as previous meeting" questions: compare the two meeting dates' rates
4. FocusEconomics provides concise summaries: `"[bank] holds fire [month year] FocusEconomics"`
5. For "increase/decrease/hold" questions: search for the specific meeting outcome

## Public Health Data
- **US Measles cases by Jan 31, 2026**: 588 (CDC confirmed); ≥500 YES, <600
- CDC updates measles tracker weekly
- Search: `"CDC measles cases [year] [month] tracker"`

## Additional Key Data Points (March 2026)
- **Brazil SELIC rate March 18, 2026**: COPOM **CUT** SELIC by 0.25% to **14.75%** (first rate cut; 'Brazil's central bank starts easing cycle, cuts Selic rate to 14.75%')
- **Lumber price March 20, 2026**: ~$578-580 USD/1000 board feet (option D: $550-$600 range per Trading Economics)

## Additional Key Data Points (March 2026 - from batch 0013)
- **Bank of England (BoE) Bank Rate Feb 5, 2026**: MPC voted 5-4 to HOLD at **3.75%**
- **Bank of England (BoE) Bank Rate March 19, 2026**: MPC voted UNANIMOUSLY to HOLD at **3.75%** (same as Feb 5, 2026)
- **ECB Deposit Facility Rate March 19, 2026**: ECB Governing Council held UNCHANGED at **2.00%** (same as Feb 5, 2026)
- **Italy judicial reform referendum (March 22-23, 2026)**: Turnout ~59% (exceeded 50% threshold); reform REJECTED (53.75% "no" vs 46.25% "yes")
- **GBP/CNY central parity rate March 19, 2026**: 1 GBP = 9.1504 CNY; 100 GBP = 915.04 CNY (People's Bank of China official rate)

## Forex Data Strategy
- People's Bank of China (PBOC) publishes daily central parity rates
- Search: "PBOC central parity rate [currency pair] [date]" or "人民币汇率中间价 [date]"
- Official source: safe.gov.cn or pbc.gov.cn
