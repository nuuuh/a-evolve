#!/usr/bin/env bash
# Fork maintenance helpers.  Do not run automatically.
set -euo pipefail

cd "$(dirname "$0")"

cmd=${1:-help}

case "$cmd" in
    status)
        # Summary of where we are relative to upstream + V2 root.
        echo "=== fork status ==="
        echo "Branch:         $(git rev-parse --abbrev-ref HEAD)"
        echo "HEAD:           $(git log HEAD -1 --format='%h %s')"
        echo "Upstream anchor: $(cat .upstream-base 2>/dev/null || echo '(missing)')"
        if git remote | grep -q upstream; then
            echo "Upstream HEAD:  $(git rev-parse upstream/main 2>/dev/null || echo '(not fetched)')"
        fi
        echo
        echo "Data symlink target: $(readlink data) → $(readlink -f data || echo '(broken)')"
        echo
        echo "V2 root experiments diff (if any):"
        if [ -d ../experiments ]; then
            diff -rq experiments ../experiments 2>/dev/null | head -20 || true
        fi
        ;;
    fetch-upstream)
        # Fetch upstream — does NOT rebase. The UnifiedEngine refactor is
        # due upstream; an auto-rebase across it would clobber V2's engine.
        # Run ``git rebase upstream/main`` manually after reviewing changes.
        echo "Fetching upstream…"
        git fetch upstream
        echo
        echo "Anchor:        $(cat .upstream-base)"
        echo "Upstream HEAD: $(git rev-parse upstream/main)"
        echo
        echo "To review incoming commits:"
        echo "    git log upstream/main --oneline ^\$(cat .upstream-base)"
        ;;
    sync-v2)
        # Refresh driver files that V2 root owns. Run when V2 updates
        # its solve_all_with_evolution.py / hypothesis scripts / experiments.
        echo "Syncing driver + experiment files from V2 root…"
        cp ../solve_all_with_evolution.py ./
        cp ../ctf_dojo_hypothesis.sh ../futurex_hypothesis.sh ../poly_hypothesis.sh ./
        chmod +x ./*.sh
        rsync -a --delete ../experiments/ ./experiments/
        echo "done."
        ;;
    help|*)
        cat <<'EOF'
Usage: ./sync.sh <command>

Commands:
  status          Show fork branch, upstream anchor, and V2 drift.
  fetch-upstream  Fetch upstream/main (read-only; no rebase).
  sync-v2         Pull driver + experiments from the V2 root tree.

Upstream rebase is deliberately manual — the UnifiedEngine refactor
scheduled upstream deletes packages V2 depends on.  See
``CLAUDE.md`` (Phase 8) for the migration procedure.
EOF
        ;;
esac
