#!/usr/bin/env python3
"""Income Agent Hub — local control plane API + SQLite ledger."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_PATH = DATA / "hub.db"
HUNT_SCRIPT = Path.home() / ".grok/skills/income-agent/scripts/hunt-lite.py"
LEADS_JSON = Path.home() / ".grok/skills/income-agent/references/leads-candidates.json"
SHEET_ID = os.environ.get("INCOME_AGENT_SHEET_ID", "10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs")

STAGES = [
    "new",
    "review",
    "proposed",
    "approved",
    "in_progress",
    "grok",
    "codex",
    "delivered",
    "invoiced",
    "paid",
    "rejected",
]

app = FastAPI(title="Income Agent Hub", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                platform TEXT,
                title TEXT,
                url TEXT,
                budget TEXT,
                score INTEGER,
                stage TEXT NOT NULL DEFAULT 'new',
                proposal TEXT,
                notes TEXT,
                kpi_target TEXT,
                revenue_planned REAL,
                revenue_actual REAL,
                deadline TEXT,
                agent_queue TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                event_type TEXT,
                payload TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                report_type TEXT,
                body TEXT,
                created_at TEXT
            );
            """
        )


class OrderIn(BaseModel):
    platform: str = ""
    title: str
    url: str = ""
    budget: str = ""
    score: int = 0
    notes: str = ""


class StagePatch(BaseModel):
    stage: str
    notes: str = ""


class ProposalIn(BaseModel):
    proposal: str


class AgentDispatch(BaseModel):
    agent: str = Field(pattern="^(grok|codex)$")
    task: str


class ReportIn(BaseModel):
    report_type: str
    body: str


def log_event(conn: sqlite3.Connection, order_id: str | None, event_type: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO events (order_id, event_type, payload, created_at) VALUES (?,?,?,?)",
        (order_id, event_type, json.dumps(payload, ensure_ascii=False), utcnow()),
    )


def queue_sheet_row(sheet: str, row: list[Any]) -> None:
    queue = DATA / "sheets-queue.jsonl"
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"sheet": sheet, "row": row, "ts": utcnow()}, ensure_ascii=False) + "\n")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": utcnow()}


@app.post("/hunt")
def hunt(min_score: int = 8, telegram: bool = False) -> dict[str, Any]:
    if not HUNT_SCRIPT.exists():
        raise HTTPException(404, "hunt-lite.py not found")
    cmd = ["python3", str(HUNT_SCRIPT), "--min-score", str(min_score)]
    if telegram:
        cmd.append("--telegram")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    imported = 0
    if LEADS_JSON.exists():
        leads = json.loads(LEADS_JSON.read_text(encoding="utf-8"))
        with db() as conn:
            for lead in leads[:15]:
                oid = str(uuid.uuid4())
                conn.execute(
                    """INSERT OR IGNORE INTO orders
                    (id, platform, title, url, budget, score, stage, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        oid,
                        lead.get("category", lead.get("platform", "")),
                        lead.get("title", "Без названия"),
                        lead.get("url", ""),
                        lead.get("budget", ""),
                        int(lead.get("score", 0)),
                        "new",
                        utcnow(),
                        utcnow(),
                    ),
                )
                imported += 1
                queue_sheet_row(
                    "Orders",
                    [
                        oid,
                        lead.get("category", ""),
                        lead.get("title", ""),
                        lead.get("url", ""),
                        lead.get("budget", ""),
                        lead.get("score", 0),
                        "new",
                        "",
                        utcnow(),
                    ],
                )
            log_event(conn, None, "hunt", {"imported": imported, "exit": proc.returncode})
            conn.commit()
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
        "imported": imported,
    }


@app.get("/orders")
def list_orders(stage: str | None = None, limit: int = 50) -> list[dict]:
    with db() as conn:
        if stage:
            rows = conn.execute(
                "SELECT * FROM orders WHERE stage=? ORDER BY score DESC, updated_at DESC LIMIT ?",
                (stage, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY score DESC, updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


@app.post("/orders")
def create_order(body: OrderIn) -> dict:
    oid = str(uuid.uuid4())
    now = utcnow()
    with db() as conn:
        conn.execute(
            """INSERT INTO orders
            (id, platform, title, url, budget, score, stage, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (oid, body.platform, body.title, body.url, body.budget, body.score, "new", body.notes, now, now),
        )
        log_event(conn, oid, "created", body.model_dump())
        conn.commit()
    queue_sheet_row("Orders", [oid, body.platform, body.title, body.url, body.budget, body.score, "new", body.notes, now])
    return {"id": oid}


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(404, "order not found")
    return dict(row)


@app.patch("/orders/{order_id}/stage")
def patch_stage(order_id: str, body: StagePatch) -> dict:
    if body.stage not in STAGES:
        raise HTTPException(400, f"invalid stage, use one of {STAGES}")
    now = utcnow()
    with db() as conn:
        cur = conn.execute(
            "UPDATE orders SET stage=?, notes=COALESCE(notes,'') || ?, updated_at=? WHERE id=?",
            (body.stage, f"\n[{now}] {body.notes}" if body.notes else "", now, order_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "order not found")
        log_event(conn, order_id, "stage", {"stage": body.stage, "notes": body.notes})
        conn.commit()
    queue_sheet_row("Orders", [order_id, "", "", "", "", "", body.stage, body.notes, now])
    return {"ok": True, "stage": body.stage}


@app.post("/orders/{order_id}/proposal")
def save_proposal(order_id: str, body: ProposalIn) -> dict:
    now = utcnow()
    with db() as conn:
        cur = conn.execute(
            "UPDATE orders SET proposal=?, stage='proposed', updated_at=? WHERE id=?",
            (body.proposal, now, order_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "order not found")
        log_event(conn, order_id, "proposal", {"len": len(body.proposal)})
        conn.commit()
    return {"ok": True}


@app.post("/orders/{order_id}/dispatch")
def dispatch_agent(order_id: str, body: AgentDispatch) -> dict:
    """Queue work for local Grok/Codex — operator must approve outbound actions separately."""
    order = get_order(order_id)
    task_file = DATA / f"task-{order_id}-{body.agent}.md"
    task_file.write_text(
        f"# Task for {body.agent.upper()}\n\n"
        f"Order: {order['title']}\n"
        f"URL: {order['url']}\n\n"
        f"{body.task}\n",
        encoding="utf-8",
    )
    now = utcnow()
    stage = "grok" if body.agent == "grok" else "codex"
    with db() as conn:
        conn.execute(
            "UPDATE orders SET stage=?, agent_queue=?, updated_at=? WHERE id=?",
            (stage, str(task_file), now, order_id),
        )
        log_event(conn, order_id, "dispatch", {"agent": body.agent, "task_file": str(task_file)})
        conn.commit()
    queue_sheet_row("AgentQueue", [order_id, body.agent, str(task_file), body.task[:500], now])
    return {"ok": True, "task_file": str(task_file), "message": f"Задача записана. Откройте {body.agent} и выполните файл."}


@app.post("/reports")
def add_report(body: ReportIn) -> dict:
    rid = str(uuid.uuid4())
    now = utcnow()
    with db() as conn:
        conn.execute(
            "INSERT INTO reports (id, report_type, body, created_at) VALUES (?,?,?,?)",
            (rid, body.report_type, body.body, now),
        )
        log_event(conn, None, "report", {"type": body.report_type})
        conn.commit()
    queue_sheet_row("Reports", [rid, body.report_type, body.body[:1000], now])
    return {"id": rid}


@app.get("/dashboard")
def dashboard() -> dict[str, Any]:
    with db() as conn:
        by_stage = {
            r["stage"]: r["c"]
            for r in conn.execute("SELECT stage, COUNT(*) c FROM orders GROUP BY stage").fetchall()
        }
        revenue = conn.execute(
            "SELECT COALESCE(SUM(revenue_actual),0) a, COALESCE(SUM(revenue_planned),0) p FROM orders"
        ).fetchone()
    return {
        "stages": by_stage,
        "revenue_actual": revenue["a"],
        "revenue_planned": revenue["p"],
        "sheet_id": SHEET_ID,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("HUB_PORT", "8765")))