#!/usr/bin/env bash
# Append an amount to the spend tracker. Usage:
#   bash backend/scripts/log_spend.sh 0.42 "phase-7 arm-a batch run"
# Idempotent: writes new total to data/results/.spend_total.txt.
set -euo pipefail

AMT="${1:?usage: log_spend.sh AMOUNT_USD [LABEL]}"
LABEL="${2:-(no label)}"
TRACKER="data/results/.spend_total.txt"
LEDGER="data/results/.spend_ledger.tsv"

mkdir -p "$(dirname "$TRACKER")"
[ -f "$TRACKER" ] || echo "0.00" > "$TRACKER"

CURRENT=$(cat "$TRACKER" | tr -d '\n' | tr -d '$')
NEW=$(awk -v c="$CURRENT" -v a="$AMT" 'BEGIN { printf "%.4f", c + a }')

echo "$NEW" > "$TRACKER"
echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ)\t${AMT}\t${NEW}\t${LABEL}" >> "$LEDGER"

echo "Logged \$$AMT for '$LABEL'. New total: \$$NEW"
