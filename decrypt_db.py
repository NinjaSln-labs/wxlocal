"""微信 4.1+ 解密模块"""
import os
import shutil
from scan_keys_v41 import copy_and_decrypt, decrypt_database, derive_enc_key, get_db_salt

# 兼容旧接口
def decrypt_with_fallback(src_path: str, passphrase_hex: str, dst_path: str) -> bool:
    passphrase = bytes.fromhex(passphrase_hex)
    return copy_and_decrypt(src_path, passphrase, dst_path)
