FUTUREX VERIFICATION CRITERIA:

For each pipeline, test these scenarios:

FINANCE PIPELINE:
- Query: "NVDA stock price January 15 2026" → must return exact close
- Query: "Shanghai Composite Index 000001.SS" → must return CN market data
- Query: "Bitcoin price" → must return crypto data
- Verify: returned price is a specific number, not a headline

GENERAL NEWS PIPELINE:
- Query: "Oscar nominations 2026" → must return dated headlines
- Query with date filter: results must be BEFORE cutoff_date
- Query in Chinese (hl=zh-CN): must return Chinese results
- Verify: each result has a date, not just "recent news"

SPORTS PIPELINE:
- Query: "Premier League standings January 2026" → exact rankings
- Query: specific match result → exact score
- Verify: structured data (team: X, score: Y), not narrative

CHINESE CONTENT PIPELINE:
- Query: "哪吒2 豆瓣评分" → exact Douban rating as a number
- Query: Maoyan box office → exact figures
- Verify: data extracted from Chinese source, not English proxy

PIPELINE QUALITY CHECKS:
- Output is agent-readable: could an LLM extract the answer in one read?
- Output is under 2000 chars: no raw HTML or full-page dumps.
- Date filtering works: no future data leaking past cutoff.
- Fallback works: if primary source fails, secondary returns data.
- Error handling: bad input returns "", does not crash.

COMMON FAILURE MODES TO CHECK:
- Pipeline returns "No results" or empty string for valid queries
- Pipeline returns raw HTML instead of extracted text
- Pipeline returns data from AFTER the cutoff date
- Pipeline times out (>15s) on sandbox network
- Pipeline crashes on non-ASCII characters (Chinese, Japanese)
