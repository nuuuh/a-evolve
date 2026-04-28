DOMAIN-SPECIFIC RESEARCH PRIORITIES:

FINANCE REGIME:
- Yahoo Finance Chart API v8: exact OHLCV for any ticker + date range.
  Covers US stocks, HK (.HK), Shanghai (.SS), Shenzhen (.SZ), crypto
  (-USD), ETFs, indices (^GSPC, ^DJI, ^IXIC, 000001.SS).
- Stooq.com CSV: historical prices via URL parameters, no API key.
- Alpha Vantage: free tier with API key, good for intraday data.
- Eastmoney/Sina Finance: Chinese A-shares, funds, bond yields.
- Test with specific ticker + date, verify exact closing price.

GENERAL NEWS REGIME:
- Google News RSS: `https://news.google.com/rss/search?q=...&hl=en`
  returns timestamped headlines. Supports language/region parameters
  (hl=zh-CN for Chinese, hl=ja for Japanese).
- Wayback Machine CDX API: fetch archived page state at a date.
- Wikipedia revision API: get article content as-of a specific date.
- DuckDuckGo HTML: broad search, but often times out in sandbox.

SPORTS REGIME:
- ESPN API endpoints: scores, standings, schedules.
- Wikipedia sports tables: tournament brackets, league standings.
- Transfermarkt (for football/soccer): player values, match results.
- Test: can you get the exact score of a specific match on a date?

CHINESE CONTENT REGIME:
- Douban API/scraping: movie ratings, book ratings.
- Maoyan: box office data (may need scraping with specific headers).
- Baidu search: `https://www.baidu.com/s?wd=...` with date params.
- zh.wikipedia.org API: same as English but for Chinese topics.
- Bilibili: video stats, trending lists.
- Test: can you get exact Douban rating for a specific movie?

TECHNOLOGY/AI REGIME:
- GitHub API: release dates, star counts, contributor stats.
- HuggingFace API: model benchmarks, download counts.
- ArXiv API: paper publication dates, citation counts.
- Product Hunt / TechCrunch (via Google News RSS with site: filter).

RESEARCH IS NOT JUST API DISCOVERY — also evaluate:
1. SCRAPING STRATEGY: Does the raw response need HTML parsing,
   JSON extraction, CSV parsing, or XML (RSS) parsing? Document
   the exact parsing steps needed.
2. OUTPUT QUALITY: Does the extracted data give the solver a clear,
   unambiguous answer? "NVDA close: $142.50 on 2026-01-15" is good.
   "Several tech stocks rose..." is useless.
3. DATE FILTERING: Can the source return data for a SPECIFIC past
   date? Or does it only show "latest"? Date-filtered sources are
   far more valuable.
4. RATE LIMITS: Does it throttle after N requests? The solver may
   call the pipeline 10-20 times per task.
5. FALLBACK CHAINS: For each regime, identify 2-3 sources that
   complement each other. Document which subtypes each covers and
   where they fail, so the builder can construct proper chains.
