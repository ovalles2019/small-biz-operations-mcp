"""Resolve folder for finance CSVs: env SMALL_BIZ_OPS_FINANCE_DATA > config file > bundled sample_data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from small_biz_ops_mcp import store

PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_SAMPLE_DIR = PACKAGE_DIR / "sample_data"
FINANCE_CONFIG_NAME = "finance_config.json"


def _config_file() -> Path:
    return store.db_path().parent / FINANCE_CONFIG_NAME


def _read_config() -> dict[str, Any]:
    path = _config_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_config(data: dict[str, Any]) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def config_override_dir() -> Path | None:
    raw = _read_config().get("finance_data_dir")
    if not raw or not str(raw).strip():
        return None
    p = Path(str(raw).strip()).expanduser().resolve()
    return p if p.is_dir() else None


def resolve_finance_data_dir() -> Path:
    env = os.environ.get("SMALL_BIZ_OPS_FINANCE_DATA")
    if env and str(env).strip():
        p = Path(env.strip()).expanduser().resolve()
        if p.is_dir():
            return p
    co = config_override_dir()
    if co is not None:
        return co
    return BUNDLED_SAMPLE_DIR


def finance_source_label() -> str:
    if os.environ.get("SMALL_BIZ_OPS_FINANCE_DATA", "").strip():
        return "env"
    if config_override_dir() is not None:
        return "config"
    return "bundled"


def expected_csv_names() -> tuple[str, ...]:
    return (
        "daily_sales.csv",
        "delivery_sales.csv",
        "payroll_monthly.csv",
        "cost_of_goods_monthly.csv",
        "rent_monthly.csv",
        "utilities_monthly.csv",
        "inventory_purchases.csv",
    )


def finance_metadata() -> dict[str, Any]:
    root = resolve_finance_data_dir()
    expected = expected_csv_names()
    present = {name: (root / name).is_file() for name in expected}
    return {
        "finance_data_dir": str(root),
        "source": finance_source_label(),
        "bundled_sample_dir": str(BUNDLED_SAMPLE_DIR),
        "operations_db": str(store.db_path()),
        "config_file": str(_config_file()),
        "csv_present": present,
        "all_required_present": all(present.values()),
    }


def set_finance_data_directory(directory: str | None) -> dict[str, Any]:
    """Persist override next to operations.db, or clear when directory is empty/whitespace."""
    if directory is None or not str(directory).strip():
        path = _config_file()
        if path.is_file():
            path.unlink()
        return {
            "ok": True,
            "cleared": True,
            "finance_data_dir": str(resolve_finance_data_dir()),
            "source": finance_source_label(),
        }
    p = Path(directory.strip()).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"Not a directory or does not exist: {p}")
    _write_config({"finance_data_dir": str(p)})
    return {
        "ok": True,
        "cleared": False,
        "finance_data_dir": str(resolve_finance_data_dir()),
        "source": finance_source_label(),
    }
