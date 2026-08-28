"""Backend configuration.

Plain module-level constants for the foundation. Swap for pydantic-settings or
environment-driven config in a later checkpoint if it earns its keep.
"""

from __future__ import annotations

import os

SERVICE_NAME = "evidenceguard-backend"
VERSION = "0.1.0"

# CORS: the Vite dev server. Comma-separate to add more origins via env.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("EG_CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

# Upload guard rails (enforced in the verify router).
MAX_FILES_PER_BUNDLE = int(os.getenv("EG_MAX_FILES", "10"))
MAX_FILE_BYTES = int(os.getenv("EG_MAX_FILE_BYTES", str(25 * 1024 * 1024)))  # 25 MB
