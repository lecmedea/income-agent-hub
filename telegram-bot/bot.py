#!/usr/bin/env python3
"""@Agent00AI_bot — Telegram control panel for Income Agent."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV = Path.home() / ".grok/skills/income-agent/.env"
HUB = os.environ.get("INCOME_AGENT_HUB", "http://127.0.0.1:8765")


def load_env() -> dict[str, str]:
    data: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    for key in ("INCOME_AGENT_TG_BOT_TOKEN", "INCOME_AGENT_TG_CHAT_ID"):
        if os.environ.get(key):
            data[key] = os.environ[key]
    return data


class HubClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None
        if body is not None:
            data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    def hunt(self, telegram: bool = True) -> dict:
        q = "?telegram=1" if telegram else ""
        return self._req("POST", f"/hunt{q}")

    def orders(self, stage: str | None = None) -> list:
        path = "/orders" + (f"?stage={urllib.parse.quote(stage)}" if stage else "")
        return self._req("GET", path)

    def dispatch(self, oid: str, agent: str, task: str) -> dict:
        return self._req("POST", f"/orders/{oid}/dispatch", {"agent": agent, "task": task})

    def stage(self, oid: str, stage: str, notes: str = "") -> dict:
        return self._req("PATCH", f"/orders/{oid}/stage", {"stage": stage, "notes": notes})

    def dashboard(self) -> dict:
        return self._req("GET", "/dashboard")


class TelegramBot:
    def __init__(self, token: str, allowed_chat: str, hub: HubClient) -> None:
        self.token = token
        self.allowed = str(allowed_chat)
        self.hub = hub
        self.offset = 0

    def api(self, method: str, params: dict | None = None) -> dict:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        data = urllib.parse.urlencode(params or {}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    def send(self, chat_id: str, text: str, reply_markup: dict | None = None) -> None:
        params: dict = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"}
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        self.api("sendMessage", params)

    def keyboard(self) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Hunt", "callback_data": "hunt"},
                    {"text": "📋 Заказы", "callback_data": "orders"},
                ],
                [
                    {"text": "📊 Dashboard", "callback_data": "dashboard"},
                    {"text": "🤖 Grok queue", "callback_data": "queue_grok"},
                ],
                [
                    {"text": "💻 Codex queue", "callback_data": "queue_codex"},
                    {"text": "📑 Отчёт", "callback_data": "report"},
                ],
            ]
        }

    def handle(self, chat_id: str, text: str) -> None:
        if str(chat_id) != self.allowed:
            self.send(chat_id, "⛔ Доступ только для оператора.")
            return

        cmd = (text or "").strip().split()[0].lower() if text else ""

        if cmd in ("/start", "/menu"):
            self.send(
                chat_id,
                "<b>Agent00AI</b> — пульт Income Agent\n\n"
                "Команды:\n"
                "/hunt — поиск лидов FL.ru\n"
                "/orders — топ заказов\n"
                "/approve N — одобрить заказ #N в списке\n"
                "/grok N — отправить в Grok\n"
                "/codex N — отправить в Codex\n"
                "/dashboard — KPI\n"
                "/sheet — ссылка на таблицу",
                self.keyboard(),
            )
            return

        if cmd == "/hunt":
            self.send(chat_id, "🔍 Запускаю hunt-lite…")
            try:
                res = self.hub.hunt(telegram=False)
                self.send(chat_id, f"✅ Импортировано: {res.get('imported',0)}\n\n<pre>{res.get('stdout','')[-1500:]}</pre>")
            except Exception as exc:
                self.send(chat_id, f"❌ Hub error: {exc}\nЗапустите: income-agent-hub/scripts/start-hub.sh")
            return

        if cmd == "/orders":
            try:
                orders = self.hub.orders()[:10]
                if not orders:
                    self.send(chat_id, "Пока нет заказов. /hunt")
                    return
                lines = []
                for i, o in enumerate(orders, 1):
                    lines.append(
                        f"<b>{i}.</b> [{o.get('score','?')}/10] {o.get('stage')}\n"
                        f"{o.get('title','')[:80]}\n"
                        f"<code>{o.get('id','')[:8]}</code> {o.get('url','')}"
                    )
                self.send(chat_id, "\n\n".join(lines), self.keyboard())
            except Exception as exc:
                self.send(chat_id, f"❌ {exc}")
            return

        if cmd.startswith("/approve"):
            try:
                idx = int(text.split()[1]) - 1
                orders = self.hub.orders()
                oid = orders[idx]["id"]
                self.hub.stage(oid, "approved", "Одобрено из Telegram")
                self.send(chat_id, f"✅ Одобрено: {orders[idx]['title'][:60]}")
            except Exception as exc:
                self.send(chat_id, f"Использование: /approve 1\nОшибка: {exc}")
            return

        if cmd.startswith("/grok") or cmd.startswith("/codex"):
            agent = "grok" if cmd.startswith("/grok") else "codex"
            try:
                idx = int(text.split()[1]) - 1
                orders = self.hub.orders()
                o = orders[idx]
                task = (
                    f"Подготовь черновик отклика и план сдачи для заказа:\n"
                    f"{o['title']}\n{o['url']}\n"
                    f"Бюджет: {o.get('budget','?')}\n"
                    f"Оператор: ИП Бежаев. Без отправки без одобрения."
                )
                res = self.hub.dispatch(o["id"], agent, task)
                self.send(chat_id, f"🚀 В очередь {agent.upper()}:\n<code>{res.get('task_file','')}</code>")
            except Exception as exc:
                self.send(chat_id, f"Использование: /{agent} 1\nОшибка: {exc}")
            return

        if cmd == "/dashboard":
            try:
                d = self.hub.dashboard()
                self.send(
                    chat_id,
                    f"📊 <b>Dashboard</b>\n"
                    f"Стадии: <pre>{json.dumps(d.get('stages',{}), ensure_ascii=False, indent=2)}</pre>\n"
                    f"План ₽: {d.get('revenue_planned',0)}\n"
                    f"Факт ₽: {d.get('revenue_actual',0)}",
                )
            except Exception as exc:
                self.send(chat_id, f"❌ {exc}")
            return

        if cmd == "/sheet":
            d = self.hub.dashboard()
            self.send(chat_id, f"📑 Таблица:\n{d.get('sheet_url','')}")
            return

        self.send(chat_id, "Неизвестная команда. /menu", self.keyboard())

    def handle_callback(self, chat_id: str, data: str) -> None:
        if data == "hunt":
            self.handle(chat_id, "/hunt")
        elif data == "orders":
            self.handle(chat_id, "/orders")
        elif data == "dashboard":
            self.handle(chat_id, "/dashboard")
        elif data == "report":
            self.send(chat_id, "Отчёт: /dashboard + Google Sheet")
        elif data in ("queue_grok", "queue_codex"):
            self.send(chat_id, "Укажите номер: /grok 1 или /codex 1")
        else:
            self.handle(chat_id, "/menu")

    def poll(self) -> None:
        self.send(self.allowed, "🟢 <b>Agent00AI</b> онлайн. /menu")
        while True:
            try:
                res = self.api("getUpdates", {"offset": self.offset, "timeout": 30})
                for upd in res.get("result", []):
                    self.offset = upd["update_id"] + 1
                    if "message" in upd:
                        m = upd["message"]
                        self.handle(str(m["chat"]["id"]), m.get("text", ""))
                    elif "callback_query" in upd:
                        cq = upd["callback_query"]
                        self.handle_callback(str(cq["message"]["chat"]["id"]), cq.get("data", ""))
                        self.api("answerCallbackQuery", {"callback_query_id": cq["id"]})
            except urllib.error.HTTPError as exc:
                print("HTTP", exc.read().decode()[:200])
            except Exception as exc:
                print("ERR", exc)


def main() -> None:
    env = load_env()
    token = env.get("INCOME_AGENT_TG_BOT_TOKEN", "")
    chat = env.get("INCOME_AGENT_TG_CHAT_ID", "")
    if not token or not chat:
        raise SystemExit("Set INCOME_AGENT_TG_BOT_TOKEN and INCOME_AGENT_TG_CHAT_ID in .env")
    TelegramBot(token, chat, HubClient(HUB)).poll()


if __name__ == "__main__":
    main()