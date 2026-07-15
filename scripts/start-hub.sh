#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/daemon"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export INCOME_AGENT_SHEET_ID="${INCOME_AGENT_SHEET_ID:-10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs}"
echo "Hub API: http://127.0.0.1:8765"
exec .venv/bin/python hub.py