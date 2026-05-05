The solver benefits from ABUNDANT retrievals from DIVERSE sources.
Every new data source you integrate expands what the solver can answer.

The baseline only has Wikipedia + DuckDuckGo. Your code adds structured
API data that appears BEFORE the Wikipedia/web fallbacks in search results.

INTEGRATION QUALITY:
- Parse responses into clean, readable text (no raw HTML/JSON dumps)
- Include source attribution and dates for reliability assessment
- Enforce cutoff_date at the API level: pass date range parameters
  to search APIs rather than filtering after the fact. Relative dates
  like "2 hours ago" cannot be reliably filtered post-hoc
- Error handling per source — one failing shouldn't block others
- The more sources integrated, the broader the solver's capability
