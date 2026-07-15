#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Income Agent 007"
APP_DIR="/Applications/${APP_NAME}.app"

echo "==> Hub venv"
"$ROOT/scripts/start-hub.sh" &
HUB_PID=$!
sleep 3
kill $HUB_PID 2>/dev/null || true

echo "==> Electron app"
cd "$ROOT/desktop-app"
if [[ ! -d node_modules ]]; then
  npm install --no-fund --no-audit
fi
npm run pack

BUILT=$(find "$ROOT/desktop-app/dist" -maxdepth 2 -name "*.app" | head -1)
if [[ -z "$BUILT" ]]; then
  echo "Build failed — run: cd desktop-app && npm run pack"
  exit 1
fi

rm -rf "$APP_DIR"
cp -R "$BUILT" "$APP_DIR"
chmod +x "$APP_DIR/Contents/MacOS/"*

echo "==> LaunchAgent Hub (автозапуск API)"
PLIST="$HOME/Library/LaunchAgents/ru.azimut.income-agent-hub.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ru.azimut.income-agent-hub</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/scripts/start-hub.sh</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/income-agent-hub.log</string>
  <key>StandardErrorPath</key><string>/tmp/income-agent-hub.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅ Установлено: $APP_DIR"
echo "✅ Hub API: http://127.0.0.1:8765"
echo "Запуск бота: $ROOT/scripts/start-telegram-bot.sh"