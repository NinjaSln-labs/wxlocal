"""Configuration: env, paths, WeChat data roots."""
from wxlocal.config._root import PROJECT_ROOT
from wxlocal.config.config import DATA_ROOT, DECRYPTED_DIR, OUTPUT_DIR, find_user_db_storage
from wxlocal.config.env_loader import load_env

__all__ = [
    "PROJECT_ROOT",
    "load_env",
    "DATA_ROOT",
    "OUTPUT_DIR",
    "DECRYPTED_DIR",
    "find_user_db_storage",
]
