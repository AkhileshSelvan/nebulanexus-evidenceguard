"""Test-session setup.

Forces the case store onto an in-memory SQLite DB so the test suite never
touches a file on disk and each `pytest` run starts from a clean slate. This
must run before anything imports `app.config` / `app.db`, which is why it's
plain module-level code in `conftest.py` (pytest always loads conftest
before collecting test modules in the same directory).
"""

from __future__ import annotations

import os

os.environ["EG_DB_PATH"] = ":memory:"
