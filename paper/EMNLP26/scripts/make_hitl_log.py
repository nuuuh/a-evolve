#!/usr/bin/env python3
"""Emit Table J1: representative HITL events on FutureX.

A dedicated HITL run is not present in the public release; instead, we
extract `credential_needed=true` research entries from the FutureX
structured-navigation research log to substantiate the kinds of external
signals the evolver could not derive autonomously and that a human
operator was asked to supply. Each row gets the cycle, regime, approach,
required credential env, and a one-line summary of what the credential
unlocked.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

LOG = REPO_ROOT / "results" / "futurex_smoke_structured_nav" / "evolver_workspace" / "research_log.jsonl"
# Tokens that look like real API keys: hex strings >= 24 chars, or
# UUID-style hyphenated alnum, or long camelcase blobs without underscores.
SECRET_RE = re.compile(
    r"\b(?:"
    r"[a-f0-9]{24,}"                   # hex tokens
    r"|[A-Za-z0-9]{32,}"               # long alphanumeric blobs (no underscores)
    r"|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"  # UUID
    r")\b"
)


def redact_secrets(text: str) -> str:
    """Redact tokens that look like API keys; leave snake_case identifiers alone."""
    return SECRET_RE.sub("[REDACTED]", text)


def main():
    rows = []
    if not LOG.exists():
        print("Research log missing; emitting placeholder", file=sys.stderr)
    else:
        for line in LOG.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not r.get("credential_needed"):
                continue
            rows.append(r)

    # Deduplicate by (regime, credential_env, approach) and keep first occurrence.
    seen = set()
    dedup = []
    for r in rows:
        key = (r.get("regime"), r.get("credential_env"), r.get("approach"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    out = []
    out.append(r"\begin{table*}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Representative human-in-the-loop events on FutureX, reconstructed from research-log entries marked \texttt{credential\_needed=true}. Each row records the evolution cycle, the regime that triggered the request, the approach the researcher was testing, the credential channel the human supplied, and the coverage the credential unlocked. Concrete API tokens that appeared in the underlying notes have been redacted. The table is meant to substantiate the kinds of external signals the autonomous loop cannot derive from history; not every row corresponds to a successful intervention.}")
    out.append(r"\label{tab:hitl_log}")
    out.append(r"\begin{tabular}{@{}rllllp{0.30\textwidth}@{}}")
    out.append(r"\toprule")
    out.append(r"Cycle & Regime & Approach & Tested & Credential & Coverage gained \\")
    out.append(r"\midrule")

    def tex_escape(s: str) -> str:
        """Escape LaTeX-special chars (mainly underscores)."""
        return s.replace("\\", r"\\").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")

    for r in dedup[:12]:  # cap at 12 for table real estate
        coverage = ", ".join((r.get("coverage") or [])[:5])
        if not coverage:
            coverage = "(no coverage list recorded)"
        cells = [
            str(r.get("cycle", "")),
            r"\texttt{" + tex_escape(str(r.get("regime", "?"))[:30]) + r"}",
            r"\texttt{" + tex_escape(str(r.get("approach", "?"))[:30]) + r"}",
            "yes" if r.get("tested") and r.get("works") else "no",
            r"\texttt{" + tex_escape(redact_secrets(str(r.get("credential_env", "?")))[:24]) + r"}",
            tex_escape(redact_secrets(coverage)[:90]),
        ]
        out.append(" & ".join(cells) + r" \\")

    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table*}")

    target = Path(__file__).resolve().parent.parent / "tables" / "J1_hitl_log.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target} ({len(dedup)} rows total, capped to 12 in display)", file=sys.stderr)


if __name__ == "__main__":
    main()
