"""Shim — use wxlocal.pipelines.chat_watch.export."""
from wxlocal.pipelines.chat_watch.export import *  # noqa: F403
from wxlocal.pipelines.chat_watch.export import export_contact, main

if __name__ == "__main__":
    main()
