"""SQLite persistence for small business operations."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'normal',
    due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    vendor TEXT,
    note TEXT,
    expense_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    follow_up_date TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventory (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'unit',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interactions(customer_id);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    root = os.environ.get("SMALL_BIZ_OPS_DATA")
    if root:
        base = Path(root).expanduser()
    else:
        base = Path.home() / ".small_biz_ops_mcp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "operations.db"


def init_db() -> None:
    path = db_path()
    with _lock:
        conn = sqlite3.connect(path, timeout=30)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


def _conn() -> sqlite3.Connection:
    path = db_path()
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


# --- Tasks ---


def create_task(
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            cur = c.execute(
                """
                INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at)
                VALUES (?, ?, 'open', ?, ?, ?, ?)
                """,
                (title.strip(), (description or "").strip() or None, priority, due_date, now, now),
            )
            c.commit()
            tid = cur.lastrowid
            row = c.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
            assert row is not None
            return _row_to_dict(row)
        finally:
            c.close()


def list_tasks(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with _lock:
        c = _conn()
        try:
            if status:
                rows = c.execute(
                    """
                    SELECT * FROM tasks WHERE status = ?
                    ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, id DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY CASE status WHEN 'open' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,
                             CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            c.close()


def update_task_status(task_id: int, status: str) -> dict[str, Any] | None:
    allowed = {"open", "in_progress", "done", "cancelled"}
    if status not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            c.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id),
            )
            c.commit()
            row = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            c.close()


# --- Expenses ---


def log_expense(
    amount: float,
    category: str,
    vendor: str | None = None,
    note: str | None = None,
    expense_date: str | None = None,
) -> dict[str, Any]:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    cents = int(round(amount * 100))
    day = expense_date or datetime.now(timezone.utc).date().isoformat()
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            cur = c.execute(
                """
                INSERT INTO expenses (amount_cents, category, vendor, note, expense_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cents,
                    category.strip(),
                    (vendor or "").strip() or None,
                    (note or "").strip() or None,
                    day,
                    now,
                ),
            )
            c.commit()
            eid = cur.lastrowid
            row = c.execute("SELECT * FROM expenses WHERE id = ?", (eid,)).fetchone()
            assert row is not None
            return _row_to_dict(row)
        finally:
            c.close()


def list_expenses(start_date: str | None = None, end_date: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 500))
    with _lock:
        c = _conn()
        try:
            q = "SELECT * FROM expenses WHERE 1=1"
            params: list[Any] = []
            if start_date:
                q += " AND expense_date >= ?"
                params.append(start_date)
            if end_date:
                q += " AND expense_date <= ?"
                params.append(end_date)
            q += " ORDER BY expense_date DESC, id DESC LIMIT ?"
            params.append(limit)
            rows = c.execute(q, params).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            c.close()


# --- Customers ---


def upsert_customer(
    name: str,
    customer_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    cid = customer_id or str(uuid.uuid4())
    with _lock:
        c = _conn()
        try:
            existing = c.execute("SELECT id FROM customers WHERE id = ?", (cid,)).fetchone()
            if existing:
                c.execute(
                    """
                    UPDATE customers
                    SET name = ?, email = ?, phone = ?, company = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name.strip(),
                        (email or "").strip() or None,
                        (phone or "").strip() or None,
                        (company or "").strip() or None,
                        (notes or "").strip() or None,
                        now,
                        cid,
                    ),
                )
            else:
                c.execute(
                    """
                    INSERT INTO customers (id, name, email, phone, company, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid,
                        name.strip(),
                        (email or "").strip() or None,
                        (phone or "").strip() or None,
                        (company or "").strip() or None,
                        (notes or "").strip() or None,
                        now,
                        now,
                    ),
                )
            c.commit()
            row = c.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
            assert row is not None
            return _row_to_dict(row)
        finally:
            c.close()


def add_customer_interaction(
    customer_id: str,
    summary: str,
    follow_up_date: str | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            parent = c.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not parent:
                raise ValueError(f"Unknown customer_id: {customer_id}")
            cur = c.execute(
                """
                INSERT INTO interactions (customer_id, summary, follow_up_date, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (customer_id, summary.strip(), follow_up_date, now),
            )
            c.commit()
            iid = cur.lastrowid
            row = c.execute("SELECT * FROM interactions WHERE id = ?", (iid,)).fetchone()
            assert row is not None
            return _row_to_dict(row)
        finally:
            c.close()


def list_customers(search: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with _lock:
        c = _conn()
        try:
            if search and search.strip():
                term = f"%{search.strip()}%"
                rows = c.execute(
                    """
                    SELECT * FROM customers
                    WHERE name LIKE ? OR IFNULL(email,'') LIKE ? OR IFNULL(company,'') LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (term, term, term, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM customers ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            c.close()


def get_customer(customer_id: str) -> dict[str, Any] | None:
    with _lock:
        c = _conn()
        try:
            cust = c.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not cust:
                return None
            inter = c.execute(
                "SELECT * FROM interactions WHERE customer_id = ? ORDER BY created_at DESC LIMIT 20",
                (customer_id,),
            ).fetchall()
            return {
                "customer": _row_to_dict(cust),
                "recent_interactions": [_row_to_dict(r) for r in inter],
            }
        finally:
            c.close()


# --- Inventory ---


def stock_set(sku: str, name: str, quantity: int = 0, unit: str = "unit") -> dict[str, Any]:
    sku_key = sku.strip()
    if not sku_key:
        raise ValueError("sku is required")
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            c.execute(
                """
                INSERT INTO inventory (sku, name, quantity, unit, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    name = excluded.name,
                    quantity = excluded.quantity,
                    unit = excluded.unit,
                    updated_at = excluded.updated_at
                """,
                (sku_key, name.strip(), quantity, unit.strip() or "unit", now),
            )
            c.commit()
            row = c.execute("SELECT * FROM inventory WHERE sku = ?", (sku_key,)).fetchone()
            assert row is not None
            return _row_to_dict(row)
        finally:
            c.close()


def stock_adjust(sku: str, delta: int) -> dict[str, Any] | None:
    sku_key = sku.strip()
    now = _utc_now()
    with _lock:
        c = _conn()
        try:
            row = c.execute("SELECT quantity FROM inventory WHERE sku = ?", (sku_key,)).fetchone()
            if not row:
                return None
            new_q = int(row["quantity"]) + delta
            if new_q < 0:
                raise ValueError("quantity cannot go negative")
            c.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? WHERE sku = ?",
                (new_q, now, sku_key),
            )
            c.commit()
            row2 = c.execute("SELECT * FROM inventory WHERE sku = ?", (sku_key,)).fetchone()
            return _row_to_dict(row2) if row2 else None
        finally:
            c.close()


def list_inventory(low_stock_threshold: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 500))
    with _lock:
        c = _conn()
        try:
            if low_stock_threshold is not None:
                rows = c.execute(
                    "SELECT * FROM inventory WHERE quantity <= ? ORDER BY quantity, sku LIMIT ?",
                    (low_stock_threshold, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM inventory ORDER BY name LIMIT ?",
                    (limit,),
                ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            c.close()


# --- Snapshot ---


def operations_snapshot() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date().isoformat()
    with _lock:
        c = _conn()
        try:
            open_tasks = c.execute(
                "SELECT COUNT(*) FROM tasks WHERE status IN ('open','in_progress')"
            ).fetchone()[0]
            expense_row = c.execute(
                "SELECT SUM(amount_cents) FROM expenses WHERE expense_date >= ?",
                (month_start,),
            ).fetchone()
            month_spend = (expense_row[0] or 0) / 100.0
            cust_count = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            low = c.execute(
                "SELECT COUNT(*) FROM inventory WHERE quantity <= 5"
            ).fetchone()[0]
            return {
                "open_or_in_progress_tasks": open_tasks,
                "month_to_date_expenses_usd": round(month_spend, 2),
                "customer_count": cust_count,
                "inventory_skus_low_stock_le_5": low,
                "database_path": str(db_path()),
            }
        finally:
            c.close()


def format_money_from_row(expense: dict[str, Any]) -> dict[str, Any]:
    out = dict(expense)
    cents = out.pop("amount_cents", None)
    if cents is not None:
        out["amount_usd"] = round(cents / 100.0, 2)
    return out


def dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
