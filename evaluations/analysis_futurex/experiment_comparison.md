# FutureX Experiment Comparison

All experiments evaluated on the same 282 tasks (aligned by task index).

## Accuracy

| Experiment | Search | Accuracy | Avg turns | Avg tokens |
|---|---|---|---|---|
| no_search | None | 34.0% (96/282) | 4.0 | 22K |
| wiki_only | Wikipedia Revision API | 35.8% (101/282) | 15.9 | 92K |
| tavily | Wikipedia + Tavily | 40.8% (115/282) | 14.5 | 89K |
| **h0b** | **Wikipedia + DDGS+htmldate** | **50.4% (142/282)** | **12.2** | **76K** |
| **h1** | **Evolution + same as h0b** | **51.7% (92/178)\*** | **12.6** | **81K** |
| live_ddg | DuckDuckGo (unrestricted) | 57.1% (161/282) | 12.0 | 54K |

## Evolved Artifacts

| Layer | Artifact | Before | After | Growth |
|---|---|---|---|---|
| Prompt | `prompts/system.md` | 2,050 chars | 35,635 chars | 17x |
| Skills | 7 domain skills | 0 | 55,566 chars | new |
| Tools | `analyze_task.py` | 0 | 46,981 chars | new |
| Memory | `memories.jsonl` | 0 | 185 entries (60K chars) | new |
| **Total** | | **2K chars** | **200K chars** | **100x** |


