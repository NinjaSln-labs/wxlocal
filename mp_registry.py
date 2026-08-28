"""Shim — use wxlocal.export.mp_registry."""
from wxlocal.export.mp_registry import *  # noqa: F403
from wxlocal.export.mp_registry import main

if __name__ == "__main__":
    main()
