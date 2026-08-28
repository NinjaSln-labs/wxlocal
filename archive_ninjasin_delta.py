"""Shim — use wxlocal.pipelines.chat_watch.archive."""
from wxlocal.pipelines.chat_watch.archive import *  # noqa: F403
from wxlocal.pipelines.chat_watch.archive import main

if __name__ == "__main__":
    main()
