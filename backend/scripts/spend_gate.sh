#!/usr/bin/env bash
# Spend gate: blocks quorum-eval invocations if accumulated spend exceeds the
# hard-stop threshold (default $300, configurable via QUORUM_SPEND_HARD_STOP_USD).
# Raised $75 -> $142 -> $200 -> $250 -> $300 by explicit user approval (2026-05-30:
# +$100 for the v3 NEJM-CPC campaign; 2026-05-31: ->$250 to fund the once-only holdout
# SC k=5 x max_turns=30 at the measured ~$1.41/case; 2026-05-31: ->$300 to comfortably
# complete k=5 holdout + fair baseline with margin under the rail).
# Other Bash calls pass through. Designed to be called from .claude/settings.json
# as a PreToolUse hook on the Bash tool.
set -euo pipefail

INPUT="${1:-}"
HARD_STOP="${QUORUM_SPEND_HARD_STOP_USD:-300}"
WARN="${QUORUM_SPEND_WARN_USD:-290}"
TRACKER="data/results/.spend_total.txt"

# Only gate quorum-eval and the v2 benchmark runner. Everything else is fine.
if ! echo "$INPUT" | grep -qE "quorum-eval (run|judge|ensemble|score)|run_v2_benchmark|claude_api_call"; then
  exit 0
fi

# Ensure tracker exists; if missing, treat as $0 spent
if [ ! -f "$TRACKER" ]; then
  echo "0.00" > "$TRACKER"
fi

CURRENT=$(cat "$TRACKER" | tr -d '\n' | tr -d '$')

# Numeric comparison via awk (bash builtin doesn't do floats)
OVER=$(awk -v c="$CURRENT" -v h="$HARD_STOP" 'BEGIN { print (c >= h) ? 1 : 0 }')
NEAR=$(awk -v c="$CURRENT" -v w="$WARN" 'BEGIN { print (c >= w) ? 1 : 0 }')

if [ "$OVER" = "1" ]; then
  echo "BLOCKED by spend gate: \$$CURRENT >= hard-stop \$$HARD_STOP." >&2
  echo "Increment the cap via QUORUM_SPEND_HARD_STOP_USD only with explicit user approval." >&2
  exit 2
fi

if [ "$NEAR" = "1" ]; then
  echo "WARNING: spend \$$CURRENT is within \$$((HARD_STOP - WARN)) of the hard stop." >&2
fi

exit 0
