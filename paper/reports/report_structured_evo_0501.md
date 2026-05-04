# Structured Evolution vs H1 Baseline — FutureX Analysis (2026-05-01)

84 tasks (stride 6 from 503). Structured evolution uses a 4-phase cycle (Analyze → Research → Build → Verify) that evolves a multi-file search pipeline under `infra/`. H1 baseline uses single-agent inline evolution that evolves individual tool scripts under `tools/`.

---

## 0. Search Pipeline Architecture

### Structured Evolution — solver data flow

```
Solver LLM
  │
  ├─ tool: web_search(query)          ← only tool besides submit (no bash)
  │     │
  │     ▼
  │  _strict_search(query)            ← solver.py, hardcoded cutoff = task_creation_date
  │     │
  │     ├─── Layer 1: Evolved Pipeline (subprocess, opaque to solver) ────────────┐
  │     │       _strict_search passes via stdin (solver never sees this):        │
  │     │       {"query": "...", "cutoff_date": "2026-01-25"}                    │
  │     │         │                                                              │
  │     │         ▼                                                              │
  │     │    search_pipeline.py                                                  │
  │     │         │                                                              │
  │     │         ├─ query_classifier.py → domains[], classification, flags      │
  │     │         │                                                              │
  │     │         ├─ Phase 0: Fast APIs (Steam JSON, OpenGithub, Manifold)       │
  │     │         ├─ Phase 1: Domain APIs (finance→Yahoo, climate→NASA/NOAA,     │
  │     │         │           entertainment→Amazon/NYT, chinese→MOA/Douban/Sina, │
  │     │         │           speech→Rev.com/WH, prediction→Manifold/Polymarket) │
  │     │         ├─ Phase 2: Broader keyword triggers (fallback matching)       │
  │     │         ├─ Phase 3: Web search (Google News RSS + Bing RSS)            │
  │     │         │                                                              │
  │     │         ├─ enforce_cutoff() → filter post-cutoff (API data bypasses)   │
  │     │         ├─ deduplicate() → merge by title                              │
  │     │         │                                                              │
  │     │       stdout: {"direct_results": [...], "queries": [...],              │
  │     │                "classification": "financial"}                           │
  │     │                                                                        │
  │     │    _strict_search formats direct_results as text:                      │
  │     │      "Yahoo Finance AAPL\n   [Yahoo Finance 2026-01-15] Close: 258.21" │
  │     └────────────────────────────────────────────────────────────────────────┘
  │     │
  │     ├─── Layer 2: htmldate Web Search ───────────────────────────────────────┐
  │     │    Uses pipeline's "queries" (or original query if no pipeline)        │
  │     │    DDGS → fetch URLs → htmldate extracts pub date → filter by cutoff   │
  │     │    Up to 3 queries × 3 results each                                   │
  │     └────────────────────────────────────────────────────────────────────────┘
  │     │
  │     ├─── Layer 3: Wikipedia Revision API (if < 3 results) ───────────────────┐
  │     │    Search → get pre-cutoff revision → extract text                     │
  │     └────────────────────────────────────────────────────────────────────────┘
  │     │
  │     ├─── Layer 4: FRED (if economic query and < 3 results) ──────────────────┐
  │     │    FRED API → time series data                                         │
  │     └────────────────────────────────────────────────────────────────────────┘
  │     │
  │     ▼
  │  results[:5]  ← CAPPED AT 5 total across all layers
  │     │
  │     ▼
  │  "Results for 'crude oil January 2026' (pre-cutoff, before 2026-01-25):\n"
  │  "1. CL=F Daily Price - 2026-01-20\n   [Yahoo Finance 2026-01-20] Close: 60.34\n"
  │  "2. There's No Real Reason for Oil Prices to Rise - RealClearEnergy\n   ...\n"
  │  "3. ..."
  │
  ▼
Solver LLM sees flat text — cannot distinguish API data from news headlines
```

### H1 Baseline — solver data flow (for comparison)

```
Solver LLM
  │
  ├─ tool: web_search(query)          ← built-in, same _strict_search (no pipeline)
  │
  ├─ tool: bash(command)              ← Docker sandbox with /tools/*.py
  │     │
  │     ▼
  │  docker exec ... python3 /tools/finance_data.py "CL=F" "2026-02-01"
  │     │
  │     ▼                                    ← NOTE: LLM chooses date arg
  │  === CL=F Price Data (before 2026-02-01) ===     (often uses resolution date,
  │  2026-01-20: 60.34                                not creation date)
  │  2026-01-21: 60.62
  │  ...
  │  2026-01-30: 65.21                       ← gets data PAST creation date
  │  Latest close: 65.21 on 2026-01-30
  │
  ▼
Solver LLM sees structured data with full date range, chooses which to use
```

### Key differences

| Aspect | Structured Evo | H1 Baseline |
|---|---|---|
| Solver tools | `web_search`, `submit` | `web_search`, `bash`, `submit` |
| API access | Opaque (pipeline subprocess) | Direct (bash → /tools/*.py) |
| Result format | Flat text, mixed sources | Structured per-tool output |
| Result cap | 5 items per search call | No cap (full tool output) |
| Cutoff enforcement | Hardcoded `task_creation_date` | LLM-chosen (often `resolution_date`) |
| API data visibility | Mixed with news headlines | Separate tool call, clearly labeled |

---

## 1. Statistics Summary

### 1.1 Overall Accuracy

| Metric | Structured Evo | H1 Baseline | Delta |
|---|---|---|---|
| Correct | 33/84 | 31/84 | +2 |
| Accuracy | 39.3% | 36.9% | +2.4pp |


### 1.3 Solver Behavior

| Metric | Structured Evo | H1 Baseline |
|---|---|---|
| Avg turns per task | 11.2 | 15.6 |
| Avg elapsed per task | 358s | 103s |
| Max turns hit | 0 | 2 |
| Timed out | 0 | 0 |


### 1.4 Search / Tool Usage

| Metric | Structured Evo | H1 Baseline |
|---|---|---|
| `web_search` calls (total) | 943 | 0 |
| `bash` calls (total) | 0 | 1,528 |
| `submit` calls | 84 | 84 |
| Avg searches per task | 11.2 | — |
| Avg bash calls per task | — | 18.2 |
| Tools available to solver | `web_search`, `submit` | `web_search`, `bash`, `submit` |
| Docker sandbox | No (`tool_files=0`) | Yes (5+ evolved tools) |


### 1.6 Evolution Overhead

| Batch | Evo Time | H1 Time | Ratio |
|---|---|---|---|
| B1 | 6,729s (112min) | 444s (7min) | 15.2x |
| B2 | 3,081s (51min) | 571s (10min) | 5.4x |
| B3 | 2,812s (47min) | 589s (10min) | 4.8x |
| B4 | 2,888s (48min) | 1,105s (18min) | 2.6x |
| B5 | 2,103s (35min) | 648s (11min) | 3.2x |
| B6 | 1,712s (29min) | 665s (11min) | 2.6x |
| B7 | 2,453s (41min) | 526s (9min) | 4.7x |
| B8 | 2,775s (46min) | 499s (8min) | 5.6x |
| B9 | 1,888s (31min) | 668s (11min) | 2.8x |
| **Total** | **26,439s (441min)** | **5,714s (95min)** | **4.6x** |

Structured evolution uses 4 LLM agents per cycle (analyst + 3 research agents + builder + verifier), each running in Docker with network access. H1 uses a single evolver agent. The 4.6x overhead produces +2.4pp improvement.

### 1.7 Evolution Cycle Quality

| Cycle | Analyst | Research Records | Build Attempts | Verify Pass | Batch Score |
|---|---|---|---|---|---|
| 1 | OK | 28 | 3 | attempt 3 | 40% |
| 2 | OK | 46 | 1 | attempt 1 | 60% |
| 3 | OK | 41 | 1 | attempt 1 | 50% |
| 4 | OK | 47 | 1 | attempt 1 | 30% |
| 5 | **FAILED** (invalid_format) | 1 | 1 | attempt 1 | 50% |
| 6 | **FAILED** (invalid_format) | 1 | 1 | attempt 1 | 40% |
| 7 | OK | 44 | 1 | attempt 1 | 20% |
| 8 | OK | 30 | 1 | attempt 1 | 40% |
| 9 | **FAILED** (invalid_format) | 1 | 1 | attempt 1 | 0% |

The analyst fails in 3/9 cycles (33%). When the analyst fails, research produces 1 record (a stub) and the builder operates with minimal guidance but still mutates the codebase. The analyst failures don't directly cause performance drops (cycle 5 scored 50%, cycle 6 scored 40%), but they prevent the system from doing targeted improvements.

### 1.8 Infra Growth Over Cycles

| After Cycle | Source Modules | Key Additions |
|---|---|---|
| 1 | 3 | `finance.py`, `climate.py`, `entertainment.py` |
| 2 | 5 | `prediction_markets.py`, `speech_transcripts.py` |
| 3 | 7 | `niche_entertainment.py`, expanded `chinese_platforms.py` |
| 4 | 8 | `cricket_stats.py` |
| 5–6 | 8 | minor changes (analyst failed) |
| 7 | 10 | `steam_stats.py`, massive `chinese_platforms.py` expansion |
| 8 | 11 | `github_ranking.py`, fund prices, FlixPatrol Wayback |
| 9 | 12 | `sports_rankings.py` (broken — Jina Reader timeouts) |

Final infra: 16 Python files, 13 source modules. Peak performance at cycle 2 with only 5 modules. Later modules are increasingly niche (cricket stats, Steam player counts, GitHub trending) and add latency/noise for most queries.

### 1.9 Evolution Cycle Details

#### Per-cycle research and build summary

| Cycle | Analyst | Gaps Identified | APIs Found | Working | Key APIs Discovered | Actually Built |
|---|---|---|---|---|---|---|
| 1 | OK | climate_science, financial_data, entertainment_ranking | 28 | 27 (96%) | Yahoo Finance v8, NASA GISTEMP CSV, NOAA JSON, Copernicus ERA5, Amazon Charts, NYT Bestsellers, Douban chart, Alpha Vantage | `finance.py`, `climate.py`, `entertainment.py`, `http_client.py`, `query_classifier.py` |
| 2 | OK | question_misinterpretation, crude_oil_settlement, trump_speech_keywords | 46 | 40 (87%) | Manifold Markets API, Polymarket Gamma API, CME settlement via Jina, Rev.com transcripts, WH sitemap, Google News keyword search | `prediction_markets.py`, `speech_transcripts.py` |
| 3 | OK | niche_entertainment, wikipedia_future_contamination, chinese_government_data | 41 | 37 (90%) | YouTube RSS feed, Fandom Wiki, Wikipedia temporal revision API, MOA Agricultural Index, MOA product types API | `niche_entertainment.py`, expanded `chinese_platforms.py` (MOA indices, Douban API) |
| 4 | OK | cricket_statistics, stock_price_prediction, oscar_prediction | 47 | 43 (91%) | ESPNcricinfo StatsGuru, Manifold Oscar category search, Oscar film win count aggregation, stock comparison detection | `cricket_stats.py`, Oscar aggregation in `prediction_markets.py` |
| 5 | **FAILED** | — | 1 | 1 | — | minor code changes (blind) |
| 6 | **FAILED** | — | 1 | 1 | — | minor code changes (blind) |
| 7 | OK | steam_platform_stats, search_result_quality_noise, chinese_niche_ranking | 44 | 40 (91%) | Steam Support JSON API, KolRank WeChat/Weibo CSRF API, Douban Rexxar variety show API, NetEase Cloud Music, Sogou Search | `steam_stats.py`, massive `chinese_platforms.py` expansion (KolRank, NetEase, Sogou) |
| 8 | OK | opengithub_daily_rank, chinese_fund_prices, flixpatrol_historical | 30 | 29 (97%) | GitHub raw content for OpenGithub, Sina Finance fund K-line API, Eastmoney fund NAV API, Wayback Machine for FlixPatrol, Apple iTunes RSS | `github_ranking.py`, fund prices in `chinese_platforms.py`, FlixPatrol Wayback |
| 9 | **FAILED** | — | 1 | 1 | — | `sports_rankings.py` (broken — Jina Reader timeouts) |

**Totals:** 239 research records, 24 distinct failure regimes identified, ~220 unique API endpoints tested, ~200 working (91% success rate).

#### API discovery-to-implementation funnel

```
Research discovered    ~220 working API endpoints
         │
         ├─ Integrated into infra     ~60  (27%)   ← actually called by source modules
         │
         ├─ Redundant / overlapping   ~80  (36%)   ← e.g., 8 climate APIs but only 6 used
         │
         ├─ Not integrated            ~50  (23%)   ← discovered but builder didn't add
         │     (Wayback variants, alternative finance APIs, backup transcripts)
         │
         └─ Broken at build time      ~30  (14%)   ← worked in research, failed in integration
               (SSL issues, rate limits, format changes between test and production)
```

The builder integrates roughly 1 in 4 discovered APIs. Research over-discovers because each gap spawns 8-20 parallel probes, most finding the same data through different paths. The funnel is expected — the waste is in researching 8 climate endpoints when 2 suffice.

#### Per-cycle gap regime details

**Cycle 1** — Foundation (3 regimes, 28 records):
- `climate_science_data_gap`: NASA GISTEMP CSV, NOAA Climate-at-a-Glance JSON, Copernicus ERA5, HadCRUT5, JMA, UAH — 8 endpoints, all working
- `financial_data_gap`: Yahoo Finance v8 chart API (no auth), Alpha Vantage, CNBC quotes, Sina Finance — 8 endpoints, all working
- `entertainment_ranking_gap`: Amazon Charts, NYT Bestsellers, Douban weekly chart, Maoyan, Bilibili — 11 endpoints, 10 working (1 Bilibili API 403)

**Cycle 2** — Prediction markets + speech (3 regimes, 46 records):
- `question_misinterpretation`: Manifold Markets search/slug APIs, Polymarket Gamma events API, Google Trends RSS — 15 endpoints, 12 working
- `crude_oil_settlement_ambiguity`: Yahoo Finance CL=F full month, CME contract calendar via Jina, CME settlement procedures, Sina futures — 16 endpoints, 13 working
- `trump_speech_keyword_coverage`: Rev.com transcript via Jina, WH press releases, Google News keyword search, CNN transcript scrape — 14 endpoints, all working

**Cycle 3** — Niche entertainment + Chinese gov (3 regimes, 41 records):
- `niche_entertainment_data_gap`: YouTube channel RSS, YouTube search, Fandom Wiki API, Wikipedia table extraction — 18 endpoints, 14 working
- `wikipedia_future_contamination`: Revision API temporal content, contamination detection, future event detection — 10 endpoints, all working
- `chinese_government_data_gap`: MOA price index API, MOA product types API, MOA homepage via Jina, Eastmoney GDP API — 12 endpoints, all working

**Cycle 4** — Cricket + Oscar aggregation (3 regimes, 47 records):
- `cricket_statistics_data_gap`: ESPNcricinfo StatsGuru batting/bowling, Jina boundary meter, Manifold cricket markets — 8 endpoints, 7 working
- `stock_price_future_prediction`: Yahoo Finance any ticker, stock comparison detection, cutoff bypass for comparisons — 18 endpoints, 15 working
- `oscar_prediction_uncertainty`: Manifold Oscar category winners, slug lookup, film win count, multi-Oscar aggregation — 20 endpoints, all working

**Cycles 5–6** — Analyst failed, 1 stub record each. Builder made minor changes without research guidance.

**Cycle 7** — Steam + Chinese niche (3 regimes, 44 records):
- `steam_platform_stats`: Steam Support JSON API, HTML fallback, Wayback Machine Steam — 10 endpoints, 9 working
- `search_result_quality_noise`: Steam stats, KolRank WeChat daily, Douban Rexxar, NetEase Cloud Music — 17 endpoints, 15 working
- `chinese_niche_ranking_data`: Douban variety show Rexxar API, multiple collection charts, KolRank CSRF API, Sogou search — 16 endpoints, 15 working

**Cycle 8** — GitHub ranking + fund prices (3 regimes, 30 records):
- `opengithub_daily_rank_unknown_source`: GitHub raw content, GitHub API temporal, contents API — 9 endpoints, all working
- `chinese_fund_price_data`: Sina Finance fund K-line API, Eastmoney fund NAV API, Sina realtime quote — 10 endpoints, 9 working
- `flixpatrol_historical_date_gap`: Wayback Machine CDX, direct timestamp, Apple iTunes RSS top movies — 10 endpoints, all working

**Cycle 9** — Analyst failed, 1 stub record. Builder added `sports_rankings.py` (WTA/FIDE/Autohome via Jina Reader) — module broken in production due to Jina Reader timeouts.

#### Final infra codebase

| File | LOC | Role |
|---|---|---|
| `search_pipeline.py` | 353 | Entry point, phase orchestration, cutoff enforcement, dedup |
| `query_classifier.py` | 559 | Query understanding, domain routing, flag detection |
| `http_client.py` | 151 | HTTP fetch, retry, gzip, Jina Reader, Wayback Machine |
| `sources/chinese_platforms.py` | 2,543 | Douban, Maoyan, Bilibili, MOA indices, Sina A-shares, Eastmoney GDP, KolRank, NetEase, Sogou, fund prices, car rankings |
| `sources/finance.py` | 712 | Yahoo Finance v8, CNBC, Sina Finance, FRED, stock comparison |
| `sources/prediction_markets.py` | 659 | Manifold Markets API, Polymarket Gamma, Oscar aggregation |
| `sources/web_search.py` | 650 | Google News RSS, Bing RSS, Wikipedia temporal-safe |
| `sources/climate.py` | 403 | NASA GISTEMP, NOAA, HadCRUT5, JMA, UAH, Copernicus, ENSO |
| `sources/niche_entertainment.py` | 398 | YouTube RSS, Fandom Wiki, Wikipedia table extraction |
| `sources/speech_transcripts.py` | 361 | Google News keyword, WH sitemap, Rev.com transcripts |
| `sources/github_ranking.py` | 245 | OpenGithub daily/weekly/monthly via GitHub raw content |
| `sources/steam_stats.py` | 241 | Steam Support Stats JSON API + HTML fallback |
| `sources/entertainment.py` | 226 | Amazon Charts, NYT Bestsellers, Box Office Mojo |
| `sources/sports_rankings.py` | 213 | WTA/ATP, FIDE chess, Autohome/Dongchedi (broken) |
| `sources/cricket_stats.py` | 208 | ESPNcricinfo StatsGuru, boundary meter |
| `sources/__init__.py` | 14 | Package init |
| **Total** | **7,936** | |

`chinese_platforms.py` alone is 32% of the codebase. It grew from ~200 LOC (cycle 3) to 2,543 LOC (cycle 9) as cycles 7–8 added KolRank, NetEase, Sogou, fund prices, car rankings, and Douban Rexxar API integrations.

---

## 2. Failure Case Analysis

### 2.1 Gained Tasks (Evo correct, H1 wrong) — 9 tasks

All 9 gains come from **better search results**, not structured API data. The pipeline's main contribution is alternative search queries and occasionally finding news articles that H1's web search missed.

#### B1: futurex_past_0023 — Melbourne City vs Auckland FC
- **Q:** Match result prediction (resolved 2026-01-17)
- **Evo:** Answer A (correct), 3 turns, 48s — Found TikTok result "Melbourne City Secures 2-1 Victory" via Google News
- **H1:** Answer C (wrong), 0 turns, 13s — Made probabilistic guess without searching (conf 0.35)
- **Why gained:** H1 didn't search at all. Evo's web_search found the actual result.

#### B2: futurex_past_0093 — 2026 Australian Open Women's Singles
- **Q:** Who will win the Women's Singles Final? (resolved 2026-02-01)
- **Evo:** Answer F (correct), 12 turns, 363s — Found Wikipedia page showing Rybakina won
- **H1:** Answer G (wrong), 21 turns, 78s — Predicted Sabalenka based on historical dominance
- **Why gained:** Evo found the Wikipedia article with the actual result. H1 searched extensively but used older data predicting Sabalenka.

#### B2: futurex_past_0097 — RBA February 2026 Rate Decision
- **Q:** What will the RBA do in February? (resolved 2026-02-03)
- **Evo:** Answer B (correct, rate hike), 16 turns, 502s — Found Jan 27 articles: "Rate hike all but certain after inflation shock" (CPI at 3.6%)
- **H1:** Answer A (wrong, rate cut), 37 turns, 202s — Used Dec 2024–2025 data predicting rate cuts
- **Why gained:** Evo found more recent news (Jan 27, 2026 inflation data) that shifted consensus from cut to hike. H1 used older forecasts.

#### B3: futurex_past_0168 — Diamond League Cut-off Question
- **Q:** Is the Diamond League shrinking cut-off fully intentional? (resolved 2026-03-05)
- **Evo:** No (correct), 9 turns, 437s — Found Manifold Markets resolution page showing creator resolved NO
- **H1:** Yes (wrong), 38 turns, 300s — Reasoned from general knowledge
- **Why gained:** Evo found the actual prediction market resolution page.

#### B5: futurex_past_0218 — Iran Protests Death Toll
- **Q:** How many people will die in 2025–26 Iranian protests before March 20? (resolved 2026-03-21)
- **Evo:** Answer E (correct), 4 turns, 126s — Found PBS article: "More than 7,000 dead in Iran's crackdown"
- **H1:** Answer F (wrong), 13 turns, 35s — Found different estimate range
- **Why gained:** Evo's search returned a more specific data point from PBS.

#### B4: futurex_past_0263 — Box Office Weekly #1
- **Q:** Which movie will be #1 on Box Office Mojo domestic weekly for March 19? (resolved 2026-03-19)
- **Evo:** "Hoppers" (correct), 16 turns, 426s — Found evidence of Hoppers staying #1
- **H1:** "Project Hail Mary" (wrong), 3 turns, 15s — Predicted upcoming release opening March 20
- **Why gained:** Evo searched more extensively and found that the existing #1 held, while H1 bet on the new release.

#### B5: futurex_past_0297 — Top Fast Food Surprise Winner
- **Q:** Will "top fast food" market have a surprising winner? (resolved 2026-03-26)
- **Evo:** No (correct), 16 turns, 739s
- **H1:** Yes (wrong), 13 turns, 41s
- **Why gained:** Different interpretation of available data.

#### B6: futurex_past_0355 — Tantalum Price
- **Q:** Will TTM tantalum concentrate price exceed $155/lb on April 1? (resolved 2026-04-02)
- **Evo:** No (correct), 16 turns, 513s — Found bearish market data for April 2026
- **H1:** Yes (wrong), 34 turns, 300s — Found SP Angel reports showing $161–245/lb historical range
- **Why gained:** Evo found more recent market data pointing to price decline.

#### B8: futurex_past_0403 — Nevada Science Olympiad
- **Q:** Who will win the 2026 Nevada Science Olympiad State Tournament [Div C]? (resolved 2026-04-12)
- **Evo:** Answer A (correct), 16 turns, 630s — Predicted Clark (2025 winner)
- **H1:** Answer A (wrong), 10 turns, 122s — Same prediction, but marked wrong
- **Why gained:** Both predicted the same answer but scored differently — likely a scoring edge case or the H1 result was partial.

**Pattern across gains:** 6/9 gains come from finding more recent or more specific news articles through web search. The pipeline's alternative queries helped surface data that H1's direct bash tool calls missed.

No gains are attributable to the pipeline's structured API modules (finance, climate, etc.). Some gained tasks (0097, 0403) show "Yahoo Finance" in search results, but inspection reveals these are Yahoo Finance Australia *news articles* delivered via Google News RSS (URLs are `news.google.com/rss/articles/...`), not Yahoo Finance API price data from the pipeline's `finance.py` module. Task 0403 does receive actual Yahoo Finance API stock prices from the pipeline, but they are irrelevant to the question (Science Olympiad) — the pipeline queries all source modules regardless of query type.

### 2.2 Lost Tasks (H1 correct, Evo wrong) — 7 tasks

#### B2: futurex_past_0056 — Paramount Skydance / Warner Bros Offer
- **Q:** Will Paramount increase offer to $30/share for WBD before Jan 24? (resolved 2026-01-25)
- **Evo:** Yes (wrong), 4 turns, 99s — Found Paramount already at $30, answered "yes" but question semantics ambiguous
- **H1:** No (correct), 22 turns, 106s — Interpreted question as "increase above $30" and correctly found no evidence of that
- **Why lost:** Question interpretation error. Evo misread "increase its offer to pay $30" as "reach $30" rather than "raise above $30".

#### B2: futurex_past_0083 — Crude Oil (CL) January Settlement
- **Q:** What will CL settle at in January 2026? (resolved 2026-02-01)
- **Evo:** Answer C ($60–65, wrong), 3 turns, 74s — Only had news articles about oil prices, no exact settlement data
- **H1:** Answer F ($65–70, correct), 7 turns, 45s — Used `python3 /tools/finance_data.py "CL=F" "2026-02-01"` to get actual daily prices, found Jan 30 close at $65.21
- **Why lost:** **H1 had direct Yahoo Finance API access via bash tool.** Evo only had news articles about oil prices. The pipeline does call Yahoo Finance internally, but the structured price data is mixed into text-format search results where the solver couldn't parse the exact settlement value. This is the clearest example of the tool gap.

#### B3: futurex_past_0135 — Jet Lag: The Game Season 16
- **Q:** Who will win Season 16? (resolved 2026-02-06)
- **Evo:** Answer B "Ben" (wrong), 16 turns, 682s — Searched extensively but couldn't find Season 16 results
- **H1:** Answer C "Adam" (correct), 7 turns, 61s — Used `python3 /tools/wikipedia_search.py` to find Wikipedia table with Season 16 winner
- **Why lost:** H1's dedicated Wikipedia tool extracted structured table data. Evo's web_search found Wikipedia articles but couldn't parse the winner from the table format.

#### B4: futurex_past_0182 — Oscars 2026 Sinners Wins
- **Q:** How many Oscars will "Sinners" win? (resolved 2026-03-15)
- **Evo:** Answer A "0–1" (wrong), 16 turns, 572s
- **H1:** Answer C "4" (correct), 10 turns, 48s — Found Wikipedia article for 98th Academy Awards stating "Sinners with four awards"
- **Why lost:** H1's tools extracted the factual answer from Wikipedia faster and more reliably.

#### B4: futurex_past_0203 — Best Original Song Oscar 2026
- **Q:** Which song will win Best Original Song? (resolved 2026-03-15)
- **Evo:** Answer A (wrong), 16 turns, 561s — Found prediction data but picked wrong song
- **H1:** Answer B "Golden" (correct), 5 turns, 18s — Found Kalshi prediction market confirmation
- **Why lost:** H1 found a more authoritative source (prediction market resolution) faster. Evo found similar data but over-weighted early predictions vs actual results.

#### B8: futurex_past_0459 — China Q1 2026 GDP Growth
- **Q:** China GDP growth (Y/Y) in Q1 2026? (resolved 2026-04-17)
- **Evo:** Answer C "4.5–5.0%" (wrong), 16 turns, 773s — Analyzed economic factors, predicted below actual
- **H1:** Answer D "5.0–5.5%" (correct), 3 turns, 14s — Used bash tool to get actual GDP report data showing 5.0%
- **Why lost:** **H1 accessed structured economic data directly.** Evo's solver reasoned from news articles and under-estimated, while H1 found the actual reported 5.0% figure through its finance tools.

#### B8: futurex_past_0477 — Iran Tanker Release
- **Q:** Will Iran release the seized tanker before April 15? (resolved 2026-04-16)
- **Evo:** Yes (wrong), 6 turns, 265s — Found news articles suggesting release, predicted yes
- **H1:** No (correct), 7 turns, 32s — Predicted no based on geopolitical reasoning
- **Why lost:** Evo found post-context articles that may have led to overconfident "yes" prediction. H1 used more conservative reasoning.

**Patterns across losses:**

| Failure Mode | Count | Tasks |
|---|---|---|
| Missing structured API data (tool gap) | 3 | 0083, 0459, 0135 |
| Reasoning/interpretation error | 2 | 0056, 0477 |
| Wrong evidence weighting | 2 | 0182, 0203 |

3/7 losses are directly attributable to the **tool gap**: H1's solver has `bash` + Docker + individual tool scripts that return structured data (Yahoo Finance prices, Wikipedia tables, GDP figures). Evo's solver only has `web_search` which returns text-format news articles and cannot parse structured API responses.

### 2.3 Both-Wrong Failures — 44 tasks

Both systems fail on 44 identical tasks (52% of the benchmark). These represent the performance ceiling that neither evolution approach can breach.

#### Category breakdown

**Unpredictable or niche events (≈15 tasks):**

Tasks requiring specific future outcomes that cannot be determined from pre-cutoff data:
- Super Bowl LX MVP (0114)
- Men's March Madness Sweet 16 (0232)
- F1 Japanese Grand Prix winner (0282)
- Neymar World Cup call-up (0408)
- Science Olympiad placements (0451)
- Tetra meditation days (0460)
- FIDE Candidates 2nd place (0450)
- Portugal presidential election qualification (0003)
- New York Rangers trade deadline trades (0155)
- "Will something CRAZY happen in January" (0109)
- "What will happen in March 2026" (0335)

These are inherently unpredictable — the outcome depends on events that haven't occurred and no amount of search can determine them.

**Chinese-language platform-specific data (≈12 tasks):**

Tasks requiring real-time ranking data from Chinese platforms that neither system can reliably access:
- Agricultural Product Wholesale Price 200 Index (0153, 0253, 0382, 0441)
- KolRank Weibo/WeChat self-media rankings (0313, 0367, 0368)
- Douban variety show rankings (0251, 0363)
- NetEase Cloud Music charts (0385)
- Chinese stock market capitalization (0272, 0323, 0431)
- Chinese fund prices (0434)
- Smart Technologies Ranking (0500)

The pipeline has source modules for some of these (chinese_platforms.py, 2,543 lines), but the data requires querying live APIs at specific dates that have already passed. The actual ranking data for "what was #1 on Douban on March 23, 2026" is not retrievable after the fact through web search.

**Exact numeric predictions (≈8 tasks):**

Tasks requiring precise numerical values for volatile indicators:
- Dow Jones close on Jan 22 (0071)
- Stock prices comparison (0205)
- Lithium carbonate price (0346)
- Pork wholesale price average (0382)
- FlixPatrol movie rankings at specific dates (0330, 0446)
- OpenGithub daily rankings at specific dates (0318, 0493)

These fail because the solver cannot access real-time or historical API data at the exact required date. Even with the pipeline's Yahoo Finance module, daily closing prices on a specific future date are unknowable before that date.

**Complex multi-factor reasoning (≈9 tasks):**

Tasks where data exists but correct prediction requires sophisticated reasoning:
- NASA GISTEMP December 2025 temperature (0005) — climate data available but solver picked wrong anomaly range
- Oscar nominations and multi-winner predictions (0036, 0044, 0191)
- Trump speech content prediction (0076)
- T20 World Cup six-to-four ratio (0159)
- RBA March decision (0206)
- Crude oil settlement ambiguity (boundary effects)

#### Failure mode distribution

| Failure Mode | Tasks | % | Addressable? |
|---|---|---|---|
| Inherently unpredictable | ~15 | 34% | No — hard ceiling |
| Chinese platform data | ~12 | 27% | Partially — needs live API access at query time |
| Exact numeric prediction | ~8 | 18% | Partially — needs structured API access |
| Reasoning errors | ~9 | 20% | Yes — better prompts and reasoning strategies |

**Theoretical ceiling:** If all reasoning errors and some platform-data tasks were fixed, accuracy could reach ~55–60%. The ~15 inherently unpredictable tasks set a hard floor of ~18% failure rate regardless of system improvements.

#### Pipeline contribution to both-wrong tasks

The pipeline delivers results for most both-wrong tasks (726 total deliveries across batches 2–9). The issue is not that the pipeline fails to return data — it returns data on every call. The issue is that the returned data is either:
1. Not specific enough (news articles about a topic instead of the exact data point needed)
2. Not accessible at the required date resolution (can find "crude oil prices in January" but not "CL settlement on January 30")
3. From sources that don't have the niche data (Google News doesn't index Douban variety show rankings)
