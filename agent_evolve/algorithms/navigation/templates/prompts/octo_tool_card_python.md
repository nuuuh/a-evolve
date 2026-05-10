**inline_python** — invoke Python 3 for arithmetic, probability, date math, or parsing.

Called via workspace_bash:
```
python3 -c "<snippet>"
```

When to use:
- Any numerical computation that would be easy to miscalculate in your head
- Probability updates (Bayes), combinatorics, regression
- Date arithmetic (delta days, business days, timezone conversion)
- JSON / CSV / table parsing

Keep snippets short (≤30 lines). For larger computations, write a file with `cat > tmp.py <<'PY' ... PY` and then run `python3 tmp.py`.

Packages available in the sandbox: `numpy`, `sympy`, `pyyaml`, `requests`, `beautifulsoup4`, `lxml`, `htmldate`, `feedparser`, `duckduckgo-search`, `pycryptodome`, `python-dateutil`, `yfinance`.
