#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Hub must be running
if ! curl -sf http://127.0.0.1:8765/health >/dev/null 2>&1; then
  echo "Запускаю Hub в фоне…"
  nohup "$ROOT/scripts/start-hub.sh" > /tmp/income-agent-hub.log 2>&1 &
  sleep 2
fi
cd "$ROOT/telegram-bot"
exec python3 bot.py