# Income Agent Hub

Пульт управления Income Agent: Telegram @Agent00AI_bot + macOS **Income Agent 007**.

## Компоненты

| Компонент | Путь |
|-----------|------|
| Hub API (SQLite + Sheets queue) | `daemon/hub.py` :8765 |
| Telegram-бот | `telegram-bot/bot.py` |
| Desktop (Bond UI) | `desktop-app/` → `/Applications/Income Agent 007.app` |
| Google Sheets setup | `scripts/google-sheets-setup.gs` |

## Быстрый старт

```bash
# 1. Установка (Hub + приложение в Программы)
chmod +x scripts/*.sh
./scripts/install-macos.sh

# 2. Telegram-бот (в отдельном терминале)
./scripts/start-telegram-bot.sh
```

Токен и chat_id: `~/.grok/skills/income-agent/.env`

## Telegram-команды

- `/menu` — пульт
- `/hunt` — поиск лидов FL.ru
- `/orders` — список заказов
- `/approve 1` — одобрить заказ
- `/grok 1` / `/codex 1` — задача локальному агенту
- `/dashboard` — KPI
- `/sheet` — Google Таблица

## Google Sheets

1. Откройте таблицу → Extensions → Apps Script
2. Вставьте `scripts/google-sheets-setup.gs`
3. Run `setupAll`

Стадии заказов: `new → review → proposed → approved → in_progress → grok/codex → delivered → invoiced → paid`

## Аватар бота

Файл: `telegram-bot/avatar.jpg`  
В @BotFather: `/setuserpic` → выберите @Agent00AI_bot → загрузите avatar.jpg

## Правила

Исходящие отклики и счета — **только после одобрения оператора**.