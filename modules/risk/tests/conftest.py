"""Make the repo root importable however pytest was invoked.

Test data builders live in ``helpers.py``, not here, so they can be imported
explicitly (``from modules.risk.tests.helpers import ...``) without relying on
pytest's sys.path insertion.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
