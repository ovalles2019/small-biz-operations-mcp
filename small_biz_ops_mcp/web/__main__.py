"""Run local web UI: python -m small_biz_ops_mcp.web"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    from small_biz_ops_mcp.web.starlette_app import app

    host = os.environ.get("SMALL_BIZ_OPS_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("SMALL_BIZ_OPS_UI_PORT", "8844"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
