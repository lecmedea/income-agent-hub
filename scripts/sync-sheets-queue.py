#!/usr/bin/env python3
"""Sync hub sheets-queue.jsonl into Google Sheet via browser clipboard instructions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "hub.db"
QUEUE = DATA / "sheets-queue.jsonl"
SHEET_ID = "10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs"
OUT = DATA / "sheets-export.tsv"


def export_orders_from_db() -> list[list]:
    if not DB.exists():
        return []
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, platform, title, url, budget, score, stage, proposal, deadline, "
        "kpi_target, revenue_planned, revenue_actual, agent_queue, updated_at, notes "
        "FROM orders ORDER BY score DESC, updated_at DESC"
    ).fetchall()
    conn.close()
    return [
        [
            r["id"], r["platform"], r["title"], r["url"], r["budget"], r["score"],
            r["stage"], r["proposal"] or "", r["deadline"] or "", r["kpi_target"] or "",
            r["revenue_planned"] or 0, r["revenue_actual"] or 0, r["agent_queue"] or "",
            r["updated_at"], r["notes"] or "",
        ]
        for r in rows
    ]


def main() -> None:
    orders = export_orders_from_db()
    lines = ["\t".join(str(c).replace("\t", " ").replace("\n", " ") for c in row) for row in orders]
    OUT.write_text("\n".join(lines), encoding="utf-8")

    pending = 0
    if QUEUE.exists():
        pending = sum(1 for _ in QUEUE.open(encoding="utf-8"))

    manifest = {
        "sheet_id": SHEET_ID,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit",
        "orders_exported": len(orders),
        "queue_pending": pending,
        "tsv_path": str(OUT),
        "instructions": [
            "1. Open sheet URL in Chrome (signed in)",
            "2. Run Apps Script setupAll from google-sheets-setup.gs if tabs missing",
            "3. Orders tab: select A2, paste TSV from sheets-export.tsv",
        ],
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()