#!/usr/bin/env python3
"""@Agent00AI_bot — Telegram control panel for Income Agent (22 languages)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "i18n"))
from i18n import SUPPORTED, language_menu, normalize_lang, t  # noqa: E402

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
    for key in ("INCOME_AGENT_TG_BOT_TOKEN", "INCOME_AGENT_TG_CHAT_ID", "INCOME_AGENT_LANG"):
        if os.environ.get(key):
            data[key] = os.environ[key]
    return data


def save_lang(code: str) -> None:
    code = normalize_lang(code)
    lines: list[str] = []
    found = False
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("INCOME_AGENT_LANG="):
                lines.append(f"INCOME_AGENT_LANG={code}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"INCOME_AGENT_LANG={code}")
    ENV.parent.mkdir(parents=True, exist_ok=True)
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


class HubClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def _req(self, method: str, path: str, body: dict | None = None) -> dict | list:
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
    def __init__(self, token: str, allowed_chat: str, hub: HubClient, lang: str) -> None:
        self.token = token
        self.allowed = str(allowed_chat)
        self.hub = hub
        self.lang = normalize_lang(lang)
        self.offset = 0
        self._orders_cache: list[dict] = []

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

    def tr(self, key: str, **kwargs: str) -> str:
        return t(key, self.lang, **kwargs)

    def keyboard(self) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": self.tr("btn_hunt"), "callback_data": "hunt"},
                    {"text": self.tr("btn_orders"), "callback_data": "orders"},
                ],
                [
                    {"text": self.tr("btn_dashboard"), "callback_data": "dashboard"},
                    {"text": self.tr("btn_report"), "callback_data": "report"},
                ],
                [
                    {"text": self.tr("btn_grok_queue"), "callback_data": "queue_grok"},
                    {"text": self.tr("btn_codex_queue"), "callback_data": "queue_codex"},
                ],
                [
                    {"text": self.tr("btn_language"), "callback_data": "lang_menu"},
                ],
            ]
        }

    def order_actions_keyboard(self, idx: int) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": self.tr("btn_approve"), "callback_data": f"act:approve:{idx}"},
                    {"text": self.tr("btn_edit"), "callback_data": f"act:edit:{idx}"},
                    {"text": self.tr("btn_reject"), "callback_data": f"act:reject:{idx}"},
                ],
                [
                    {"text": self.tr("btn_create_project"), "callback_data": f"act:project:{idx}"},
                    {"text": self.tr("btn_manual"), "callback_data": f"act:manual:{idx}"},
                ],
                [
                    {"text": self.tr("btn_grok"), "callback_data": f"act:grok:{idx}"},
                    {"text": self.tr("btn_codex"), "callback_data": f"act:codex:{idx}"},
                ],
                [
                    {"text": self.tr("btn_sheet"), "callback_data": "sheet"},
                    {"text": self.tr("btn_language"), "callback_data": "lang_menu"},
                ],
            ]
        }

    def lang_keyboard(self) -> dict:
        rows = []
        row: list[dict] = []
        for code, name in language_menu():
            row.append({"text": name, "callback_data": f"lang:{code}"})
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([{"text": "← /menu", "callback_data": "menu"}])
        return {"inline_keyboard": rows}

    def _order_at(self, idx: int) -> dict | None:
        if not self._orders_cache:
            self._orders_cache = self.hub.orders()
        if 0 <= idx < len(self._orders_cache):
            return self._orders_cache[idx]
        return None

    def _dispatch_order(self, chat_id: str, idx: int, agent: str) -> None:
        o = self._order_at(idx)
        if not o:
            self.send(chat_id, self.tr("no_orders"))
            return
        task = (
            f"Подготовь черновик отклика и план сдачи для заказа:\n"
            f"{o['title']}\n{o['url']}\n"
            f"Бюджет: {o.get('budget', '?')}\n"
            f"Оператор: ИП Бежаев. Без отправки без одобрения."
        )
        try:
            res = self.hub.dispatch(o["id"], agent, task)
            self.send(
                chat_id,
                self.tr("dispatched", agent=agent.upper(), file=res.get("task_file", "")),
                self.order_actions_keyboard(idx),
            )
        except Exception as exc:
            self.send(chat_id, self.tr("error_generic", error=str(exc)))

    def handle(self, chat_id: str, text: str) -> None:
        if str(chat_id) != self.allowed:
            self.send(chat_id, self.tr("access_denied"))
            return

        parts = (text or "").strip().split()
        cmd = parts[0].lower() if parts else ""

        if cmd in ("/start", "/menu"):
            self.send(
                chat_id,
                f"<b>{self.tr('menu_title')}</b>\n\n{self.tr('menu_help')}",
                self.keyboard(),
            )
            return

        if cmd == "/help":
            self.send(chat_id, self.tr("help_full"), self.keyboard())
            return

        if cmd == "/lang":
            self.send(chat_id, self.tr("lang_pick"), self.lang_keyboard())
            return

        if cmd == "/hunt":
            self.send(chat_id, self.tr("hunt_start"))
            try:
                res = self.hub.hunt(telegram=False)
                stdout = (res.get("stdout") or "")[-1500:]
                self.send(
                    chat_id,
                    self.tr("hunt_ok", count=str(res.get("imported", 0)), stdout=stdout),
                    self.keyboard(),
                )
                self._orders_cache = []
            except Exception as exc:
                self.send(chat_id, self.tr("hunt_error", error=str(exc)))
            return

        if cmd == "/orders":
            try:
                self._orders_cache = self.hub.orders()[:10]
                if not self._orders_cache:
                    self.send(chat_id, self.tr("no_orders"), self.keyboard())
                    return
                lines = []
                for i, o in enumerate(self._orders_cache, 1):
                    lines.append(
                        self.tr(
                            "order_line",
                            n=str(i),
                            score=str(o.get("score", "?")),
                            stage=o.get("stage", ""),
                            title=(o.get("title") or "")[:80],
                            id=(o.get("id") or "")[:8],
                            url=o.get("url", ""),
                        )
                    )
                self.send(chat_id, "\n\n".join(lines), self.order_actions_keyboard(0))
            except Exception as exc:
                self.send(chat_id, self.tr("error_generic", error=str(exc)))
            return

        if cmd.startswith("/approve"):
            try:
                idx = int(parts[1]) - 1
                o = self._order_at(idx)
                if not o:
                    raise IndexError("order")
                self.hub.stage(o["id"], "approved", "Одобрено из Telegram")
                self.send(chat_id, self.tr("approved", title=o["title"][:60]), self.order_actions_keyboard(idx))
            except Exception as exc:
                self.send(chat_id, f"{self.tr('usage_approve')}\n{exc}")
            return

        if cmd.startswith("/reject"):
            try:
                idx = int(parts[1]) - 1
                o = self._order_at(idx)
                if not o:
                    raise IndexError("order")
                self.hub.stage(o["id"], "rejected", "Отклонено из Telegram")
                self.send(chat_id, self.tr("rejected", title=o["title"][:60]), self.order_actions_keyboard(idx))
            except Exception as exc:
                self.send(chat_id, f"/reject 1\n{exc}")
            return

        if cmd.startswith("/edit"):
            try:
                idx = int(parts[1]) - 1
                note = " ".join(parts[2:]) or "—"
                o = self._order_at(idx)
                if not o:
                    raise IndexError("order")
                self.hub.stage(o["id"], o.get("stage", "review"), note)
                self.send(chat_id, self.tr("edit_ok", n=str(idx + 1)), self.order_actions_keyboard(idx))
            except Exception as exc:
                self.send(chat_id, self.tr("edit_prompt", n="1") + f"\n{exc}")
            return

        if cmd.startswith("/project"):
            try:
                idx = int(parts[1]) - 1
                o = self._order_at(idx)
                if not o:
                    raise IndexError("order")
                self.hub.stage(o["id"], "in_progress", "Проект создан из Telegram")
                self.send(chat_id, self.tr("project_created", title=o["title"][:60]), self.order_actions_keyboard(idx))
            except Exception as exc:
                self.send(chat_id, f"/project 1\n{exc}")
            return

        if cmd.startswith("/manual"):
            try:
                idx = int(parts[1]) - 1
                o = self._order_at(idx)
                if not o:
                    raise IndexError("order")
                self.hub.stage(o["id"], "in_progress", "Выполнение вручную — оператор")
                self.send(chat_id, self.tr("manual_set", title=o["title"][:60]), self.order_actions_keyboard(idx))
            except Exception as exc:
                self.send(chat_id, f"/manual 1\n{exc}")
            return

        if cmd.startswith("/grok") or cmd.startswith("/codex"):
            agent = "grok" if cmd.startswith("/grok") else "codex"
            try:
                idx = int(parts[1]) - 1
                self._dispatch_order(chat_id, idx, agent)
            except Exception as exc:
                self.send(chat_id, f"{self.tr('usage_dispatch', agent=agent)}\n{exc}")
            return

        if cmd == "/dashboard":
            try:
                d = self.hub.dashboard()
                self.send(
                    chat_id,
                    f"{self.tr('dashboard_title')}\n"
                    + self.tr(
                        "dashboard_body",
                        stages=json.dumps(d.get("stages", {}), ensure_ascii=False, indent=2),
                        planned=str(d.get("revenue_planned", 0)),
                        actual=str(d.get("revenue_actual", 0)),
                    ),
                    self.keyboard(),
                )
            except Exception as exc:
                self.send(chat_id, self.tr("error_generic", error=str(exc)))
            return

        if cmd in ("/sheet", "/report"):
            try:
                d = self.hub.dashboard()
                self.send(chat_id, self.tr("sheet_link", url=d.get("sheet_url", "")), self.keyboard())
            except Exception as exc:
                self.send(chat_id, self.tr("error_generic", error=str(exc)))
            return

        self.send(chat_id, self.tr("unknown_cmd"), self.keyboard())

    def handle_callback(self, chat_id: str, data: str) -> None:
        if str(chat_id) != self.allowed:
            return

        if data == "menu":
            self.handle(chat_id, "/menu")
            return

        if data == "hunt":
            self.handle(chat_id, "/hunt")
        elif data == "orders":
            self.handle(chat_id, "/orders")
        elif data == "dashboard":
            self.handle(chat_id, "/dashboard")
        elif data == "report":
            self.send(chat_id, self.tr("report_hint"), self.keyboard())
        elif data == "sheet":
            self.handle(chat_id, "/sheet")
        elif data in ("queue_grok", "queue_codex"):
            self.send(chat_id, self.tr("pick_order"), self.keyboard())
        elif data == "lang_menu":
            self.send(chat_id, self.tr("lang_pick"), self.lang_keyboard())
        elif data.startswith("lang:"):
            code = data.split(":", 1)[1]
            if code in SUPPORTED:
                self.lang = code
                save_lang(code)
                names = dict(language_menu())
                self.send(chat_id, self.tr("lang_set", name=names.get(code, code)), self.keyboard())
        elif data.startswith("act:"):
            _, action, idx_s = data.split(":", 2)
            idx = int(idx_s)
            if action == "approve":
                self.handle(chat_id, f"/approve {idx + 1}")
            elif action == "reject":
                self.handle(chat_id, f"/reject {idx + 1}")
            elif action == "edit":
                self.send(chat_id, self.tr("edit_prompt", n=str(idx + 1)), self.order_actions_keyboard(idx))
            elif action == "project":
                self.handle(chat_id, f"/project {idx + 1}")
            elif action == "manual":
                self.handle(chat_id, f"/manual {idx + 1}")
            elif action == "grok":
                self._dispatch_order(chat_id, idx, "grok")
            elif action == "codex":
                self._dispatch_order(chat_id, idx, "codex")
        else:
            self.handle(chat_id, "/menu")

    def poll(self) -> None:
        self.send(self.allowed, self.tr("online_msg"))
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
    lang = env.get("INCOME_AGENT_LANG", "ru")
    if not token or not chat:
        raise SystemExit("Set INCOME_AGENT_TG_BOT_TOKEN and INCOME_AGENT_TG_CHAT_ID in .env")
    TelegramBot(token, chat, HubClient(HUB), lang).poll()


if __name__ == "__main__":
    main()