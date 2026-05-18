#!/usr/bin/env python3
"""Walk through the same flows as the MCP tools (SQLite + analytics).

Run from the repo root (after `pip install -e .`):

  python demo_session.py

Use a fixed throwaway DB directory:

  python demo_session.py --data-dir /tmp/smbiz_demo

Keep your real Cursor DB untouched unless you intentionally point --data-dir at it.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

from small_biz_ops_mcp import analytics, finance_paths, store


def banner(title: str) -> None:
    print()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)


def step(name: str) -> None:
    print(f"\n▶ {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Live demo of Small Biz Ops tool equivalents.")
    parser.add_argument(
        "--data-dir",
        default=None,
        metavar="PATH",
        help="Directory for operations.db and finance_config.json (default: new temp directory).",
    )
    args = parser.parse_args()

    if args.data_dir:
        data_dir = os.path.abspath(os.path.expanduser(args.data_dir))
        os.makedirs(data_dir, exist_ok=True)
        os.environ["SMALL_BIZ_OPS_DATA"] = data_dir
        print(f"Using SMALL_BIZ_OPS_DATA={data_dir}")
    else:
        data_dir = tempfile.mkdtemp(prefix="smbiz_demo_")
        os.environ["SMALL_BIZ_OPS_DATA"] = data_dir
        print(f"Using temp SMALL_BIZ_OPS_DATA={data_dir}")

    banner("LIVE DEMO — Small Business Operations (MCP tool equivalents)")

    store.init_db()

    step("operations_snapshot()")
    print(store.dumps(store.operations_snapshot()))

    step("create_task('Order oat milk', due_date='2026-05-20', priority='high')")
    print(store.dumps(store.create_task("Order oat milk", due_date="2026-05-20", priority="high")))

    step("log_expense(42.50, 'supplies', vendor='Webstaurant', note='Lids')")
    print(
        store.dumps(
            store.format_money_from_row(
                store.log_expense(42.50, "supplies", vendor="Webstaurant", note="Lids")
            )
        )
    )

    step("list_tasks(status='open', limit=5)")
    print(store.dumps(store.list_tasks(status="open", limit=5)))

    step("get_finance_data_directory()")
    print(store.dumps(finance_paths.finance_metadata()))

    step("analyze_monthly_sales(None)")
    print(store.dumps(analytics.analyze_monthly_sales(None)))

    step("summarize_profit_margin() — latest month")
    m = analytics.summarize_profit_margin()
    last = m["by_month"][-1] if m.get("by_month") else {}
    print(store.dumps({"note": m.get("note"), "latest_month": last}))

    step("detect_expense_anomalies() — first 5 flags")
    a = analytics.detect_expense_anomalies()
    print(store.dumps({"months": a.get("months"), "anomalies": (a.get("anomalies") or [])[:5]}))

    step("compare_payroll_to_revenue()")
    print(store.dumps(analytics.compare_payroll_to_revenue()))

    step("create_weekly_owner_report() — excerpt")
    report = analytics.create_weekly_owner_report()
    max_chars = 1200
    if len(report) > max_chars:
        print(report[:max_chars] + "\n…")
    else:
        print(report)

    banner("Next steps")
    print(
        "• In Cursor: wire MCP to `python -m small_biz_ops_mcp` and ask the model to use these tools.\n"
        "• Inspector: `mcp dev small_biz_ops_mcp/server.py`\n"
        "• Dashboard: `small-biz-ops-ui` → http://127.0.0.1:8844"
    )
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
