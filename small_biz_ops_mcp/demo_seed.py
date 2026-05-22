"""Seed SQLite with sample ops data for public demos (idempotent)."""

from __future__ import annotations

from small_biz_ops_mcp import store


def _is_empty() -> bool:
    snap = store.operations_snapshot()
    return (
        snap.get("customer_count", 0) == 0
        and snap.get("open_or_in_progress_tasks", 0) == 0
        and snap.get("month_to_date_expenses_usd", 0) == 0
    )


def seed_demo_if_empty() -> bool:
    """Populate demo tasks, customers, inventory, and expenses when the DB is empty."""
    if not _is_empty():
        return False

    store.create_task("Order oat milk", due_date="2026-05-22", priority="high")
    store.create_task("Review Q2 supplier quotes", due_date="2026-05-28", priority="normal")
    store.create_task("Schedule equipment maintenance", priority="normal")
    store.update_task_status(
        store.create_task("Train new barista on POS", priority="normal")["id"],
        "in_progress",
    )

    store.log_expense(42.50, "supplies", vendor="Webstaurant", note="Cup lids")
    store.log_expense(128.00, "utilities", vendor="City Power", note="May partial")
    store.log_expense(89.99, "marketing", vendor="Instagram ads")

    c1 = store.upsert_customer(
        name="Riverfront Catering",
        email="orders@riverfront.example",
        company="Riverfront Catering Co.",
        notes="Weekly pastry pickup",
    )
    store.add_customer_interaction(
        c1["id"],
        "Confirmed standing order for Fridays; wants invoice by email.",
        follow_up_date="2026-05-25",
    )
    c2 = store.upsert_customer(
        name="Jamie Ortiz",
        phone="555-0142",
        notes="Neighborhood regular",
    )
    store.add_customer_interaction(c2["id"], "Asked about seasonal cold brew launch.")

    store.stock_set("SKU-OAT", "Oat milk (case)", quantity=3, unit="case")
    store.stock_set("SKU-CUP-12", "12oz cups", quantity=48, unit="sleeve")
    store.stock_set("SKU-BEANS", "House blend beans", quantity=12, unit="lb")
    store.stock_set("SKU-SYRUP-VAN", "Vanilla syrup", quantity=2, unit="bottle")

    return True
