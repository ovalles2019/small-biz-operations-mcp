"""Financial analytics on bundled sample CSVs or a user-provided sales CSV (stdlib only)."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from small_biz_ops_mcp import finance_paths, store

PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_SAMPLE_DIR = finance_paths.BUNDLED_SAMPLE_DIR


def _finance_root() -> Path:
    return finance_paths.resolve_finance_data_dir()


def sample_data_paths() -> dict[str, str]:
    """CSV paths in the active finance directory."""
    root = _finance_root()
    return {p.stem: str(p.resolve()) for p in sorted(root.glob("*.csv"))}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _month_key_from_date(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def resolve_sales_csv(csv_file: str | None) -> Path:
    root = _finance_root()
    if not csv_file or not csv_file.strip():
        p = root / "daily_sales.csv"
        if p.is_file():
            return p
        fb = BUNDLED_SAMPLE_DIR / "daily_sales.csv"
        if fb.is_file():
            return fb
        raise FileNotFoundError(f"daily_sales.csv not found in {root} or bundled samples.")
    raw = csv_file.strip()
    p = Path(raw).expanduser()
    if p.is_file():
        return p.resolve()
    for base in (root, Path.cwd(), BUNDLED_SAMPLE_DIR):
        q = (base / raw).resolve()
        if q.is_file():
            return q
    raise FileNotFoundError(
        f"Could not resolve csv_file={csv_file!r}. Tried absolute, finance dir, cwd, and bundled sample_data."
    )


def _parse_date(s: str) -> date:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def _parse_float(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def load_daily_sales(path: Path) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    out: list[dict[str, Any]] = []
    for r in rows:
        d = _parse_date(r.get("date") or r.get("sale_date") or "")
        if r.get("in_store_usd") is not None or r.get("delivery_usd") is not None:
            ins = _parse_float(r.get("in_store_usd") or "0")
            deliv = _parse_float(r.get("delivery_usd") or "0")
            if ins > 0:
                out.append({"date": d.isoformat(), "revenue_usd": ins, "channel": "in_store"})
            if deliv > 0:
                out.append({"date": d.isoformat(), "revenue_usd": deliv, "channel": "delivery"})
            continue
        rev = _parse_float(r.get("revenue_usd") or r.get("revenue") or "0")
        ch = (r.get("channel") or "in_store").strip().lower()
        out.append({"date": d.isoformat(), "revenue_usd": rev, "channel": ch})
    out.sort(key=lambda x: x["date"])
    return out


def load_monthly_series(path: Path, amount_key: str = "amount_usd") -> dict[str, float]:
    rows = _read_csv(path)
    acc: dict[str, float] = defaultdict(float)
    for r in rows:
        ym = (r.get("year_month") or r.get("month") or "").strip()
        if not ym:
            continue
        acc[ym] += _parse_float(r.get(amount_key) or "0")
    return dict(sorted(acc.items()))


def load_inventory_purchases_by_month() -> dict[str, float]:
    path = _finance_root() / "inventory_purchases.csv"
    rows = _read_csv(path)
    acc: dict[str, float] = defaultdict(float)
    for r in rows:
        d = _parse_date(r.get("date") or "")
        ym = _month_key_from_date(d)
        acc[ym] += _parse_float(r.get("amount_usd") or "0")
    return dict(sorted(acc.items()))


def load_delivery_sales_monthly() -> dict[str, float]:
    path = _finance_root() / "delivery_sales.csv"
    rows = _read_csv(path)
    acc: dict[str, float] = defaultdict(float)
    for r in rows:
        d = _parse_date(r.get("date") or "")
        ym = _month_key_from_date(d)
        acc[ym] += _parse_float(r.get("revenue_usd") or r.get("revenue") or "0")
    return dict(sorted(acc.items()))


def monthly_sales_from_daily(daily: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """year_month -> {total, in_store, delivery}."""
    acc: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "in_store": 0.0, "delivery": 0.0})
    for row in daily:
        d = date.fromisoformat(row["date"])
        ym = _month_key_from_date(d)
        rev = float(row["revenue_usd"])
        ch = row["channel"]
        acc[ym]["total"] += rev
        if ch == "delivery":
            acc[ym]["delivery"] += rev
        else:
            acc[ym]["in_store"] += rev
    return {k: dict(v) for k, v in sorted(acc.items())}


def analyze_monthly_sales(csv_file: str | None = None) -> dict[str, Any]:
    path = resolve_sales_csv(csv_file)
    daily = load_daily_sales(path)
    by_month = monthly_sales_from_daily(daily)
    months = list(by_month.keys())
    mom: list[dict[str, Any]] = []
    for i, ym in enumerate(months):
        cur = by_month[ym]["total"]
        prev_total = by_month[months[i - 1]]["total"] if i > 0 else None
        pct = None
        if prev_total and prev_total > 0:
            pct = round(100.0 * (cur - prev_total) / prev_total, 2)
        mix = by_month[ym]
        tot = mix["total"] or 1.0
        mom.append(
            {
                "year_month": ym,
                "revenue_usd": round(cur, 2),
                "in_store_usd": round(mix["in_store"], 2),
                "delivery_usd": round(mix["delivery"], 2),
                "delivery_pct_of_revenue": round(100.0 * mix["delivery"] / tot, 2),
                "mom_revenue_pct_change": pct,
            }
        )
    return {
        "source_csv": str(path),
        "finance_data_dir": str(_finance_root()),
        "note": "Uses active finance directory (env SMALL_BIZ_OPS_FINANCE_DATA, saved config, or bundled sample).",
        "daily_rows": len(daily),
        "monthly": mom,
    }


def _iqr_outliers(values: list[float]) -> tuple[float, float, list[int]]:
    if len(values) < 4:
        return float("-inf"), float("inf"), []
    q1, _q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    bad_idx = [i for i, v in enumerate(values) if v < lo or v > hi]
    return lo, hi, bad_idx


def _z_outliers(values: list[float], z: float = 2.0) -> list[int]:
    if len(values) < 3:
        return []
    mu = statistics.mean(values)
    sd = statistics.pstdev(values)
    if sd == 0:
        return []
    return [i for i, v in enumerate(values) if abs((v - mu) / sd) > z]


def detect_expense_anomalies() -> dict[str, Any]:
    root = _finance_root()
    payroll = load_monthly_series(root / "payroll_monthly.csv")
    cogs = load_monthly_series(root / "cost_of_goods_monthly.csv")
    rent = load_monthly_series(root / "rent_monthly.csv")
    utilities = load_monthly_series(root / "utilities_monthly.csv")
    inv = load_inventory_purchases_by_month()
    all_months = sorted(
        set(payroll) | set(cogs) | set(rent) | set(utilities) | set(inv),
        key=lambda x: x,
    )
    series: dict[str, list[float]] = {
        "payroll": [],
        "cogs": [],
        "rent": [],
        "utilities": [],
        "inventory_purchases": [],
        "total_operating": [],
    }
    for ym in all_months:
        p = payroll.get(ym, 0.0)
        cg = cogs.get(ym, 0.0)
        r = rent.get(ym, 0.0)
        u = utilities.get(ym, 0.0)
        i = inv.get(ym, 0.0)
        series["payroll"].append(p)
        series["cogs"].append(cg)
        series["rent"].append(r)
        series["utilities"].append(u)
        series["inventory_purchases"].append(i)
        series["total_operating"].append(p + cg + r + u + i)
    flags: list[dict[str, Any]] = []
    for label, vals in series.items():
        lo, hi, idx_iqr = _iqr_outliers(vals)
        idx_z = _z_outliers(vals, z=2.0)
        for i in sorted(set(idx_iqr) | set(idx_z)):
            ym = all_months[i]
            v = vals[i]
            reasons = []
            if i in idx_iqr:
                reasons.append("iqr")
            if i in idx_z:
                reasons.append("z_score_gt_2")
            flags.append(
                {
                    "year_month": ym,
                    "metric": label,
                    "amount_usd": round(v, 2),
                    "iqr_bounds_usd": [round(lo, 2), round(hi, 2)],
                    "reasons": reasons,
                }
            )
    return {
        "note": "Heuristics on synthetic monthly series (IQR + z-score). Not audit-grade.",
        "months": all_months,
        "anomalies": flags,
    }


def summarize_profit_margin() -> dict[str, Any]:
    root = _finance_root()
    daily = load_daily_sales(root / "daily_sales.csv")
    rev_m = monthly_sales_from_daily(daily)
    cogs = load_monthly_series(root / "cost_of_goods_monthly.csv")
    rent = load_monthly_series(root / "rent_monthly.csv")
    util = load_monthly_series(root / "utilities_monthly.csv")
    payroll = load_monthly_series(root / "payroll_monthly.csv")
    inv = load_inventory_purchases_by_month()
    months = sorted(set(rev_m) | set(cogs) | set(rent) | set(util) | set(payroll) | set(inv))
    rows: list[dict[str, Any]] = []
    for ym in months:
        rev = rev_m.get(ym, {}).get("total", 0.0)
        cg = cogs.get(ym, 0.0)
        r = rent.get(ym, 0.0)
        u = util.get(ym, 0.0)
        p = payroll.get(ym, 0.0)
        ip = inv.get(ym, 0.0)
        opex = r + u + p + ip
        gross_profit = rev - cg
        operating_profit = rev - cg - opex
        rows.append(
            {
                "year_month": ym,
                "revenue_usd": round(rev, 2),
                "cogs_usd": round(cg, 2),
                "gross_margin_pct": round(100.0 * gross_profit / rev, 2) if rev else None,
                "opex_ex_cogs_usd": round(opex, 2),
                "operating_margin_pct": round(100.0 * operating_profit / rev, 2) if rev else None,
            }
        )
    return {"note": "Demo margins from active finance CSVs; definitions are simplified.", "by_month": rows}


def compare_payroll_to_revenue() -> dict[str, Any]:
    root = _finance_root()
    daily = load_daily_sales(root / "daily_sales.csv")
    rev_m = monthly_sales_from_daily(daily)
    payroll = load_monthly_series(root / "payroll_monthly.csv")
    months = sorted(set(rev_m) | set(payroll), key=lambda x: x)
    out: list[dict[str, Any]] = []
    for ym in months:
        rev = rev_m.get(ym, {}).get("total", 0.0)
        pr = payroll.get(ym, 0.0)
        ratio = round(100.0 * pr / rev, 2) if rev else None
        out.append(
            {
                "year_month": ym,
                "revenue_usd": round(rev, 2),
                "payroll_usd": round(pr, 2),
                "payroll_as_pct_of_revenue": ratio,
            }
        )
    return {
        "note": (
            "Retail / light manufacturing often land roughly in the teens–high twenties "
            "for payroll % of revenue; your industry mix varies."
        ),
        "by_month": out,
    }


def generate_buyer_due_diligence_packet() -> str:
    sales = analyze_monthly_sales(None)
    margin = summarize_profit_margin()
    pr = compare_payroll_to_revenue()
    anom = detect_expense_anomalies()
    snap = store.operations_snapshot()
    lines = [
        "# Buyer due diligence packet (draft)",
        "",
        "_Disclaimer: figures below mix **live SQLite ops data** (tasks/customers/inventory counts) "
        "with **CSV finance files** from the active finance directory (see `get_finance_data_directory`). "
        "Not legal, tax, or investment advice._",
        "",
        "## 1. Executive snapshot",
        f"- Open / in-progress tasks (live DB): **{snap['open_or_in_progress_tasks']}**",
        f"- Customers on file (live DB): **{snap['customer_count']}**",
        f"- SKUs at or below 5 units (live DB): **{snap['inventory_skus_low_stock_le_5']}**",
        f"- Month-to-date expenses logged in SQLite (UTC month): **${snap['month_to_date_expenses_usd']:.2f}**",
        "",
        "## 2. Revenue (sample `daily_sales.csv`)",
        store.dumps(sales.get("monthly", [])),
        "",
        "## 3. Profitability (sample monthly COGS + opex files)",
        store.dumps(margin.get("by_month", [])),
        "",
        "## 4. Payroll vs revenue",
        store.dumps(pr.get("by_month", [])),
        "",
        "## 5. Expense anomalies (heuristic)",
        store.dumps(anom.get("anomalies", [])),
        "",
        "## 6. Suggested follow-up checklist",
        "- Confirm revenue recognition policy vs POS exports.",
        "- Tie payroll registers to GL and contractor 1099s.",
        "- Inventory cycle count vs perpetual records; shrinkage.",
        "- Related-party rent / management fees.",
        "- Customer concentration (top 10 % of sales).",
        "- Litigation, permits, and lease abstract.",
        "",
        "## 7. Data sources",
        store.dumps(sample_data_paths()),
    ]
    return "\n".join(lines)


def create_weekly_owner_report() -> str:
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=7)
    daily = load_daily_sales(_finance_root() / "daily_sales.csv")
    recent = [r for r in daily if date.fromisoformat(r["date"]) >= week_start]
    prior = [r for r in daily if week_start - timedelta(days=21) <= date.fromisoformat(r["date"]) < week_start]
    rev_w = sum(r["revenue_usd"] for r in recent)
    rev_prior_sum = sum(r["revenue_usd"] for r in prior)
    days_prior = max(1, len({r["date"] for r in prior}))
    avg_daily_prior = rev_prior_sum / days_prior if prior else 0.0
    days_w = max(1, len({r["date"] for r in recent}))
    avg_daily_week = rev_w / days_w
    margin = summarize_profit_margin()
    last_m = margin["by_month"][-1] if margin["by_month"] else {}
    anom = detect_expense_anomalies()
    lines = [
        "# Weekly owner report (draft)",
        f"_Generated (UTC): {datetime.now(timezone.utc).date().isoformat()}_",
        "",
        "## Sales pulse (sample daily file, last 7 calendar days with rows)",
        f"- Revenue in window: **${rev_w:,.2f}** across **{days_w}** day(s) with data",
        f"- Avg revenue / day (window): **${avg_daily_week:,.2f}**",
        f"- Prior 3-week blended avg / day (sample): **${avg_daily_prior:,.2f}**",
        "",
        "## Latest full P&L view in sample pack",
        store.dumps(last_m),
        "",
        "## Expense anomaly flags (same heuristics as `detect_expense_anomalies`)",
        store.dumps(anom.get("anomalies", [])[-8:]),
        "",
        "## Ops snapshot (live SQLite)",
        store.dumps(snap := store.operations_snapshot()),
        "",
        "## Prompts for you",
        "- Any large invoices or payroll spikes coming in the next 14 days?",
        "- One operational fix that would improve margin or cash this week?",
    ]
    return "\n".join(lines)
