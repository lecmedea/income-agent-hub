#!/bin/zsh
# Opens signed-in Chrome and copies Apps Script to clipboard for paste+run setupAll
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHEET_ID="${INCOME_AGENT_SHEET_ID:-10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs}"
GS="$ROOT/scripts/google-sheets-setup.gs"
TSV="$ROOT/data/sheets-export.tsv"

pbcopy < "$GS"
python3 "$ROOT/scripts/sync-sheets-queue.py" >/dev/null

echo "✅ Apps Script скопирован в буфер обмена"
echo "1. Chrome → Расширения → Apps Script"
echo "2. Вставьте (Cmd+V), сохраните, Run → setupAll"
echo "3. Orders → A2 → вставьте TSV: $TSV"

open -a "Google Chrome" "https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit"
sleep 2
open -a "Google Chrome" "https://script.google.com/home/projects/create?parent=${SHEET_ID}"