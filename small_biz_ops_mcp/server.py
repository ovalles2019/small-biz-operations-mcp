"""MCP server: tasks, expenses, customers, inventory — backed by local SQLite."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from small_biz_ops_mcp import analytics, finance_paths, store

mcp = FastMCP(
    "Small Business Operations",
    instructions=(
        "Local-first tools for small business operations: tasks, expenses, customers, "
        "and inventory (SQLite under SMALL_BIZ_OPS_DATA or ~/.small_biz_ops_mcp). "
        "Finance CSVs load from SMALL_BIZ_OPS_FINANCE_DATA, a saved directory (see set_finance_data_directory), "
        "or bundled sample_data/. analyze_monthly_sales can also target a specific CSV path."
    ),
)


@mcp.tool()
def create_task(
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    priority: str = "normal",
) -> str:
    """Create an operational task. due_date as ISO date (YYYY-MM-DD) optional."""
    row = store.create_task(title=title, description=description, due_date=due_date, priority=priority)
    return store.dumps(row)


@mcp.tool()
def list_tasks(status: str | None = None, limit: int = 50) -> str:
    """List tasks. status: open | in_progress | done | cancelled, or omit for all (prioritizes open)."""
    rows = store.list_tasks(status=status, limit=limit)
    return store.dumps(rows)


@mcp.tool()
def update_task_status(task_id: int, status: str) -> str:
    """Set task status to open, in_progress, done, or cancelled."""
    row = store.update_task_status(task_id, status)
    if not row:
        return f"No task found with id={task_id}"
    return store.dumps(row)


@mcp.tool()
def log_expense(
    amount: float,
    category: str,
    vendor: str | None = None,
    note: str | None = None,
    expense_date: str | None = None,
) -> str:
    """Record a business expense. amount in dollars; expense_date YYYY-MM-DD defaults to today (UTC)."""
    row = store.log_expense(
        amount=amount,
        category=category,
        vendor=vendor,
        note=note,
        expense_date=expense_date,
    )
    return store.dumps(store.format_money_from_row(row))


@mcp.tool()
def list_expenses(start_date: str | None = None, end_date: str | None = None, limit: int = 100) -> str:
    """List expenses with optional inclusive YYYY-MM-DD range filters."""
    rows = [store.format_money_from_row(r) for r in store.list_expenses(start_date, end_date, limit)]
    return store.dumps(rows)


@mcp.tool()
def upsert_customer(
    name: str,
    customer_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    notes: str | None = None,
) -> str:
    """Create or update a customer. Pass customer_id to update an existing record."""
    row = store.upsert_customer(
        name=name,
        customer_id=customer_id,
        email=email,
        phone=phone,
        company=company,
        notes=notes,
    )
    return store.dumps(row)


@mcp.tool()
def add_customer_interaction(
    customer_id: str,
    summary: str,
    follow_up_date: str | None = None,
) -> str:
    """Append a CRM-style interaction note for a customer. follow_up_date optional YYYY-MM-DD."""
    row = store.add_customer_interaction(customer_id, summary, follow_up_date)
    return store.dumps(row)


@mcp.tool()
def list_customers(search: str | None = None, limit: int = 50) -> str:
    """List customers; optional search matches name, email, or company (substring)."""
    rows = store.list_customers(search=search, limit=limit)
    return store.dumps(rows)


@mcp.tool()
def get_customer(customer_id: str) -> str:
    """Return one customer plus up to 20 recent interactions."""
    data = store.get_customer(customer_id)
    if not data:
        return f"No customer found with id={customer_id}"
    return store.dumps(data)


@mcp.tool()
def stock_set(sku: str, name: str, quantity: int = 0, unit: str = "unit") -> str:
    """Create or replace inventory for a SKU (sets quantity to the given value)."""
    row = store.stock_set(sku=sku, name=name, quantity=quantity, unit=unit)
    return store.dumps(row)


@mcp.tool()
def stock_adjust(sku: str, delta: int) -> str:
    """Adjust inventory quantity by delta (negative allowed down to zero)."""
    row = store.stock_adjust(sku, delta)
    if not row:
        return f"No inventory row for sku={sku}"
    return store.dumps(row)


@mcp.tool()
def list_inventory(low_stock_threshold: int | None = None, limit: int = 200) -> str:
    """List inventory. If low_stock_threshold is set, only rows with quantity <= threshold."""
    rows = store.list_inventory(low_stock_threshold=low_stock_threshold, limit=limit)
    return store.dumps(rows)


@mcp.tool()
def operations_snapshot() -> str:
    """High-level counts: open tasks, month-to-date expenses, customers, low stock SKUs, DB path."""
    return store.dumps(store.operations_snapshot())


@mcp.tool()
def get_finance_data_directory() -> str:
    """Return active finance CSV folder, how it was chosen (env / config / bundled), and which expected files exist."""
    return store.dumps(finance_paths.finance_metadata())


@mcp.tool()
def set_finance_data_directory(directory: str | None = None) -> str:
    """Save finance CSV folder path in finance_config.json next to operations.db. Pass empty/null to clear and revert."""
    try:
        return store.dumps(finance_paths.set_finance_data_directory(directory))
    except ValueError as e:
        return store.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def analyze_monthly_sales(csv_file: str | None = None) -> str:
    """Aggregate daily sales into monthly revenue, delivery mix, and month-over-month % change."""
    return store.dumps(analytics.analyze_monthly_sales(csv_file))


@mcp.tool()
def detect_expense_anomalies() -> str:
    """Flag unusual months across bundled sample payroll, COGS, rent, utilities, and inventory purchases."""
    return store.dumps(analytics.detect_expense_anomalies())


@mcp.tool()
def summarize_profit_margin() -> str:
    """Rough gross and operating margins by month using bundled sample revenue and cost files."""
    return store.dumps(analytics.summarize_profit_margin())


@mcp.tool()
def compare_payroll_to_revenue() -> str:
    """Payroll dollars and payroll-as-% of revenue by month from bundled sample data."""
    return store.dumps(analytics.compare_payroll_to_revenue())


@mcp.tool()
def generate_buyer_due_diligence_packet() -> str:
    """Markdown draft combining sample financial analytics plus live SQLite ops snapshot (synthetic + live)."""
    return analytics.generate_buyer_due_diligence_packet()


@mcp.tool()
def create_weekly_owner_report() -> str:
    """Markdown weekly brief: recent sample sales vs prior weeks, margins, anomaly flags, live ops snapshot."""
    return analytics.create_weekly_owner_report()


@mcp.resource("operations://snapshot")
def resource_snapshot() -> str:
    """Latest operations snapshot as JSON text."""
    return store.dumps(store.operations_snapshot())


@mcp.prompt()
def weekly_ops_review() -> str:
    """Prompt template for a concise weekly operations review."""
    return (
        "Using the Small Business Operations tools, pull operations_snapshot, list open tasks, "
        "list_expenses for the last 7 days, list_inventory with low_stock_threshold=5, "
        "and optionally analyze_monthly_sales, summarize_profit_margin, detect_expense_anomalies. "
        "Summarize risks, cash implications, and propose three priorities for next week in plain language."
    )


def main() -> None:
    store.init_db()
    mcp.run()


if __name__ == "__main__":
    main()
