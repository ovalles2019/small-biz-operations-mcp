"""Whether the web UI runs as a public portfolio demo."""

from __future__ import annotations

import os


def is_demo_mode() -> bool:
    raw = os.environ.get("SMALL_BIZ_OPS_DEMO", "")
    return raw.strip().lower() in ("1", "true", "yes", "on")
