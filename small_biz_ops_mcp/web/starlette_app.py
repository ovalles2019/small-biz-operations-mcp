"""Minimal Starlette app: static UI + JSON APIs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from small_biz_ops_mcp import analytics, finance_paths, store

STATIC = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: Starlette):
    store.init_db()
    yield


async def index(_: Request) -> FileResponse:
    return FileResponse(STATIC / "index.html")


async def api_finance_get(_: Request) -> JSONResponse:
    return JSONResponse(finance_paths.finance_metadata())


async def api_finance_post(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    raw = body.get("directory")
    if raw is None:
        raw = ""
    try:
        result = finance_paths.set_finance_data_directory(str(raw) if raw is not None else None)
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


async def api_snapshot(_: Request) -> JSONResponse:
    return JSONResponse(store.operations_snapshot())


def _safe(name: str, fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "data": fn()}
    except Exception as e:
        return {"ok": False, "error": str(e), "section": name}


async def api_dashboard(_: Request) -> JSONResponse:
    payload: dict[str, Any] = {
        "finance": finance_paths.finance_metadata(),
        "snapshot": store.operations_snapshot(),
        "sales": _safe("sales", lambda: analytics.analyze_monthly_sales(None)),
        "margins": _safe("margins", analytics.summarize_profit_margin),
        "payroll": _safe("payroll", analytics.compare_payroll_to_revenue),
        "anomalies": _safe("anomalies", analytics.detect_expense_anomalies),
    }
    return JSONResponse(payload)


routes = [
    Route("/", index),
    Route("/api/finance", api_finance_get, methods=["GET"]),
    Route("/api/finance", api_finance_post, methods=["POST"]),
    Route("/api/snapshot", api_snapshot, methods=["GET"]),
    Route("/api/dashboard", api_dashboard, methods=["GET"]),
    Mount("/static", StaticFiles(directory=str(STATIC)), name="static"),
]

app = Starlette(debug=False, routes=routes, lifespan=lifespan)
