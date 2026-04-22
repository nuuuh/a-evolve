# Evolver Infrastructure Evolution: The API Exploration Gap

## Summary

When given internet access and explicit instructions to explore web APIs, the Opus
evolver (128K tokens) **diagnoses search coverage as the #1 performance bottleneck
but fails to autonomously explore the broader API landscape**. It optimizes within
its comfort zone — prompt engineering, Wikipedia query refinement, DuckDuckGo HTML
scraping — rather than testing external APIs (Google Search, NewsAPI, ESPN, financial
data services) that could dramatically improve coverage.

This motivates a **human-in-the-loop** evolution design where the evolver identifies
API needs and a human provides credentials/setup.

---

## Experiment Setup

- **Evolver**: Opus 4.6, 128K tokens, `network=host` (full internet access)
- **Solver**: Sonnet 4.6, no built-in web search (`no_web_search: true`)
- **Seed**: Wikipedia revision search only (`wiki_search.py`)
- **Batch size**: 5 tasks, 20 evolution cycles
- **Evolved layers**: prompts + tools (skills/memory disabled)

## Results (20 tasks, 3 evolution cycles completed)

| Cycle | Batch Score | Tools Created |
|-------|-------------|---------------|
| 1     | 80% (4/5)   | web_search.py, fetch_url.py, api_call.py |
| 2     | 40% (2/5)   | sports_scores.py |
| 3     | 20% (1/5)   | manifold_search.py (improved sports_scores) |

Overall: 7/20 (35%), 6 tools evolved from 1 seed tool.

---

## Evidence: Evolver Identifies Search as the Bottleneck

### Evo Cycle 1 — "No web search tools available"

The evolver correctly diagnoses the problem after batch 1:

> **Key failure patterns identified:**
> 1. **Turn limit exhaustion** (tasks 0018, 0009): Agent wasted 10+ turns on
>    failed wiki_search queries with slight variations, leaving no turns for analysis
> 2. **Wiki-only search strategy** (task 0019): Agent never searched the web,
>    instead printing hardcoded "analysis" with fabricated data
> 3. **No web search tools available**: The agent had to manually construct
>    DuckDuckGo URLs via Python urllib in tasks 0006 and 0009, which was
>    effective but consumed many turns
>
> **Key success patterns identified:**
> - Task 0006 (MCSR): Agent discovered the mcsrranked.com API and got
>   definitive playoff results → correct answer with 97% confidence

Response: Created `web_search.py` (DuckDuckGo HTML scraper), `fetch_url.py`,
`api_call.py`. All use `urllib.request` — no external packages, no API keys.

### Evo Cycle 2 — "web_search is the most effective tool"

> **Critical: The agent's date is April 2026, but events resolve around Jan
> 2026 — events have ALREADY HAPPENED.** The most successful tasks (Toluca,
> Bayern, MCSR) found actual results via web_search or fetch_url. Failed
> tasks (Islanders, América, Tetra) wasted turns on wiki_search or didn't
> search at all.
>
> **web_search is the most effective tool** for sports results that already
> happened. Tasks 0029 and 0030 succeeded by using web_search early.
>
> **Failures:**
> - Task 0020 (América vs San Luis): **web_search returned nothing**, agent
>   couldn't find result despite it being a past event. Hit turn limit.

Response: Created `sports_scores.py`, reordered tools (web_search first),
added proven URL patterns (bundesliga.com, ESPN). Still no external API exploration.

### Evo Cycle 3 — "web_search returns 'No results' for many queries"

> **web_search returns "No results" for many queries** — The agent tries many
> search queries that return nothing, especially for less popular leagues
> (Saudi Pro League, A-League).
>
> **Soccerway URL mismatch** — fetch_url on soccerway.com returns wrong team
> data (Italian teams instead of Saudi/Australian teams). URLs are guessed
> incorrectly.

Response: Improved `sports_scores.py`, added fallback suggestions. Created
`manifold_search.py`. **Still no attempt to try Google Search API, NewsAPI,
ESPN API, or any authenticated data source.**

---

## Evidence: Zero API Exploration Attempts

Across all 3 evolution cycles, the evolver made **zero live API test calls**
to external services. Despite having `network=host` (full internet access)
and explicit instructions to "test these and more: Google Custom Search API,
Bing Web Search API, NewsAPI.org, ESPN, football-data.org...", the evolver:

1. **Never ran** `python3 -c "urllib.request.urlopen('https://newsapi.org/...')"`
2. **Never ran** `python3 -c "urllib.request.urlopen('https://www.googleapis.com/...')"`
3. **Never tested** any API endpoint to discover auth requirements
4. **Never created** `infra/api_requests.md` to document human-needed credentials

All bash commands were either file writes (`cat > tools/...`) or file reads
(`cat prompts/system.md`). The only API-adjacent command was a syntax check:
```
python3 tools/sports_scores.py 2>&1 | head -5
```

---

## The Comfort Zone Pattern

The evolver follows a consistent pattern every cycle:

```
1. Read workspace files (find, cat prompts/system.md, cat tools/registry.yaml)
2. Read observation logs (cat evolution/observations/batch_*.jsonl)
3. Analyze failure patterns (reasoning in assistant text)
4. Write improved prompt (cat > prompts/system.md)
5. Write improved/new tools (cat > tools/web_search.py)
6. Write skills/memory (reverted by protect())
7. Verify with git diff
```

It **never** deviates to:
```
- Test an external API endpoint
- Discover what data sources exist
- Probe authentication requirements
- Create infra/api_requests.md
```

The evolver treats every problem as solvable through better prompts and
better DuckDuckGo query strategies. When DuckDuckGo returns nothing for
"Saudi Pro League Al-Ittihad vs Al-Hilal", the evolver's response is to
add more query variations to the prompt — not to try the football-data.org
API or ESPN's endpoint.

---

## Tools Created (What the Evolver Built)

| Tool | Source | Auth Required | Created |
|------|--------|---------------|---------|
| wiki_search.py | Wikipedia Revision API | No | Seed |
| web_search.py | DuckDuckGo HTML scraping | No | Evo 1 |
| fetch_url.py | Generic URL fetcher | No | Evo 1 |
| api_call.py | Generic HTTP caller | No | Evo 1 |
| sports_scores.py | Multi-source sports search | No | Evo 2 |
| manifold_search.py | Manifold Markets API | No | Evo 3 |

All 6 tools use **free, keyless APIs**. None require authentication.

## Tools NOT Created (What a Human Would Add)

| API | What It Provides | Auth | Impact |
|-----|-----------------|------|--------|
| Google Custom Search | Broad web search (better than DDG) | API key (free 100/day) | HIGH — covers all domains |
| NewsAPI.org | News articles with date filtering | API key (free 100/day) | HIGH — current events |
| Serper.dev | Google search results as JSON | API key (free 2500/mo) | HIGH — reliable search |
| football-data.org | Football match results | API key (free tier) | MEDIUM — sports tasks |
| ESPN API | Sports scores and standings | No key but undocumented | MEDIUM — US sports |
| Alpha Vantage | Stock/forex/crypto data | API key (free 25/day) | MEDIUM — financial tasks |
| Finnhub | Real-time financial data | API key (free tier) | MEDIUM — financial tasks |
| FRED | Economic indicators | API key (free) | LOW — already in H0b |

---

## Implications for Human-in-the-Loop Evolution

This experiment reveals a fundamental limitation of autonomous infrastructure
evolution: **the evolver cannot cross the authentication boundary**.

Even with internet access, the evolver:
1. Cannot sign up for API accounts
2. Cannot provide billing information
3. Cannot agree to terms of service
4. Cannot manage API keys securely
5. Cannot evaluate cost/benefit tradeoffs of paid APIs

This motivates a **human-in-the-loop evolution** design:

```
┌─────────────────────────────────────────────────────────┐
│                   Evolution Cycle                        │
│                                                         │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Evolver   │───▶│ API Request  │───▶│   Human      │ │
│  │ (Opus LLM) │    │ Document     │    │  Operator    │ │
│  │            │    │              │    │              │ │
│  │ Diagnoses: │    │ "Need Google │    │ Signs up,    │ │
│  │ "DDG fails │    │  Search API  │    │ provides key │ │
│  │  for Saudi │    │  for sports" │    │ sets env var │ │
│  │  Pro League│    │              │    │              │ │
│  └───────────┘    └──────────────┘    └──────┬───────┘ │
│                                              │         │
│  ┌───────────┐                               │         │
│  │  Evolver   │◀──── API key now available ───┘         │
│  │ (next cycle│                                         │
│  │  uses key) │                                         │
│  └───────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

The evolver writes `infra/api_requests.md` documenting what it needs.
A human reviews, provisions credentials, and sets environment variables.
The next evolution cycle picks up the keys and builds tools that use them.

This is a **natural division of labor**: the LLM identifies data gaps and
writes integration code; the human handles authentication, payment, and
access control — tasks that require real-world identity and judgment.
