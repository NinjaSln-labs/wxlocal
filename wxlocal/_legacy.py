"""Ensure repo-root legacy modules stay importable after pip install."""
from __future__ import annotations

import sys

from wxlocal.config._root import PROJECT_ROOT

_bootstrapped = False


def bootstrap_legacy_imports() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    _bootstrapped = True
