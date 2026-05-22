# Small Business Operations MCP Agent

[![Live demo](https://img.shields.io/badge/demo-live-22c55e?style=flat-square)](https://small-biz-ops-demo.onrender.com/)

Local-first [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for day-to-day small business work: **tasks**, **expenses**, **customers / CRM notes**, **inventory**, and **sample-based financial analytics**. Live ops data lives in **SQLite** on your machine (no cloud by default); bundled CSVs are **synthetic** for demos.

## Requirements

- Python 3.10+
- [`mcp`](https://pypi.org/project/mcp/) (installed with this project)

## Install

```bash
cd /Users/oscarvalles/Small_biz_operationsMCP_agent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## CLI demo (no Cursor required)

Prints the same flows the MCP tools expose (uses a **throwaway** SQLite dir unless you pass `--data-dir`):

```bash
cd /Users/oscarvalles/Small_biz_operationsMCP_agent
source .venv/bin/activate
python demo_session.py

# Or reuse a fixed folder:
python demo_session.py --data-dir /tmp/smbiz_demo
```

## Data directory

- Default: `~/.small_biz_ops_mcp/operations.db`
- Override: set `SMALL_BIZ_OPS_DATA` to a directory path (the database file will be `operations.db` inside it).

### Finance CSV folder

Resolution order (first match wins):

1. **`SMALL_BIZ_OPS_FINANCE_DATA`** — absolute path to a directory containing the expected CSV filenames.
2. **Saved override** — `finance_config.json` in the same directory as `operations.db` (written by the web UI or MCP tool `set_finance_data_directory`).
3. **Bundled** — `small_biz_ops_mcp/sample_data/` inside the installed package.

## Web UI (local dashboard)

Minimal browser UI for the same SQLite snapshot and finance analytics.

```bash
cd /Users/oscarvalles/Small_biz_operationsMCP_agent
source .venv/bin/activate
small-biz-ops-ui
# or: python -m small_biz_ops_mcp.web
```

Then open **http://127.0.0.1:8844** (default). Override with **`SMALL_BIZ_OPS_UI_PORT`** and **`SMALL_BIZ_OPS_UI_HOST`**.

Install web dependencies if needed:

```bash
pip install -e ".[web]"
```

The UI can set the finance CSV directory (writes `finance_config.json` next to `operations.db`). If **`SMALL_BIZ_OPS_FINANCE_DATA`** is set in the environment, it takes priority over that file.

## Live demo (portfolio)

Deploy the **read-only dashboard** (bundled sample CSVs + seeded SQLite). MCP stdio stays local; the public URL is for the web UI only.

### Render (recommended)

1. Push this repo to GitHub (`ovalles2019/small-biz-operations-mcp`).
2. [Render](https://render.com) → **New** → **Blueprint** → connect the repo.
3. Render applies `render.yaml` and builds the `Dockerfile`.
4. Copy the service URL (e.g. `https://small-biz-ops-demo.onrender.com`) into your portfolio.

Demo env (set in `render.yaml` / Docker):

- `SMALL_BIZ_OPS_DEMO=1` — seeds sample tasks/customers/inventory on first boot; disables finance path edits.
- `SMALL_BIZ_OPS_DATA=/data` — SQLite on the container disk (resets on redeploy on free tier).

Health check: `GET /health`

### Docker (local smoke test)

```bash
docker build -t small-biz-ops-demo .
docker run --rm -p 8844:10000 -e PORT=10000 small-biz-ops-demo
# open http://127.0.0.1:8844
```

### Railway / Fly.io

Same image: build from `Dockerfile`, set `PORT` (platform injects it), `SMALL_BIZ_OPS_DEMO=1`, and `SMALL_BIZ_OPS_DATA` to a writable path.

## Run (stdio, for Cursor / Claude Desktop)

```bash
cd /Users/oscarvalles/Small_biz_operationsMCP_agent
source .venv/bin/activate
python -m small_biz_ops_mcp
```

Or after install:

```bash
small-biz-ops-mcp
```

## Cursor MCP configuration

Add to your MCP config (e.g. **Cursor Settings → MCP → Edit**), adjusting paths if your clone lives elsewhere:

```json
{
  "mcpServers": {
    "small-biz-ops": {
      "command": "/Users/oscarvalles/Small_biz_operationsMCP_agent/.venv/bin/python",
      "args": ["-m", "small_biz_ops_mcp"],
      "env": {
        "SMALL_BIZ_OPS_DATA": "/Users/oscarvalles/Small_biz_operationsMCP_agent/.data"
      }
    }
  }
}
```

If you prefer `uv`:

```json
{
  "mcpServers": {
    "small-biz-ops": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/oscarvalles/Small_biz_operationsMCP_agent", "python", "-m", "small_biz_ops_mcp"]
    }
  }
}
```

Restart Cursor (or reload MCP) after saving. Optionally add **`SMALL_BIZ_OPS_FINANCE_DATA`** to `env` (absolute path to your CSV folder) so MCP ignores any saved `finance_config.json` override.

## Tools

| Tool | Purpose |
|------|--------|
| `create_task` | New task (`open`); optional `due_date` (YYYY-MM-DD), `priority` |
| `list_tasks` | List tasks; optional `status` filter |
| `update_task_status` | `open` / `in_progress` / `done` / `cancelled` |
| `log_expense` | Amount in **USD**, category, optional vendor / note / date |
| `list_expenses` | Optional `start_date` / `end_date` (YYYY-MM-DD) |
| `upsert_customer` | Create or update customer; optional `customer_id` to update |
| `add_customer_interaction` | Log a CRM-style note; optional `follow_up_date` |
| `list_customers` | Optional substring `search` |
| `get_customer` | Customer + recent interactions |
| `stock_set` | Create or **replace** quantity for a SKU |
| `stock_adjust` | Increment / decrement stock |
| `list_inventory` | Optional `low_stock_threshold` filter |
| `operations_snapshot` | Counts, month-to-date expenses (UTC month), DB path |
| `get_finance_data_directory` | Active finance CSV folder, source (`env` / `config` / `bundled`), and which expected files exist |
| `set_finance_data_directory` | Save or clear finance folder in `finance_config.json` (empty clears); env `SMALL_BIZ_OPS_FINANCE_DATA` overrides |
| `analyze_monthly_sales` | Monthly revenue, delivery mix, MoM %; optional `csv_file` path (else `daily_sales.csv` in active finance dir) |
| `detect_expense_anomalies` | IQR + z-score flags on monthly payroll, COGS, rent, utilities, inventory purchases (active finance dir) |
| `summarize_profit_margin` | Gross and simplified operating margin by month (active finance dir) |
| `compare_payroll_to_revenue` | Payroll vs revenue % by month (active finance dir) |
| `generate_buyer_due_diligence_packet` | Markdown draft: analytics + live ops snapshot (**not** legal/financial advice) |
| `create_weekly_owner_report` | Markdown brief: recent sales vs prior weeks, margins, anomalies, live snapshot |

## Bundled sample CSVs (synthetic)

Shipped under `small_biz_ops_mcp/sample_data/` (Jan–Apr 2026 demo period):

| File | Contents |
|------|-----------|
| `daily_sales.csv` | Daily in-store and delivery revenue |
| `delivery_sales.csv` | Daily delivery revenue only |
| `payroll_monthly.csv` | Monthly payroll |
| `cost_of_goods_monthly.csv` | Monthly COGS |
| `rent_monthly.csv` | Monthly rent |
| `utilities_monthly.csv` | Monthly utilities (includes a March spike for anomaly demos) |
| `inventory_purchases.csv` | Dated purchase lines |

## Resources and prompts

- Resource: `operations://snapshot` — same data as `operations_snapshot`
- Prompt: `weekly_ops_review` — template for a weekly review using the tools above
