"""Shim — use wxlocal.core.decrypt / keys."""
from wxlocal.core.decrypt import *  # noqa: F403
from wxlocal.core.keys import (  # noqa: F401
    copy_and_decrypt,
    decrypt_database,
    derive_enc_key,
    get_db_salt,
)
