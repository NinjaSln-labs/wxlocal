"""微信 4.1+ 密钥提取与解密（passphrase + PBKDF2 方案）"""
import ctypes
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import tempfile
from ctypes import wintypes
from hashlib import pbkdf2_hmac
from pathlib import Path

from Crypto.Cipher import AES

from wxlocal.config.config import DATA_ROOT

PAGE_SIZE = 4096
KDF_ITER = 256000
IV_OFFSET = 4016
IV_SIZE = 16
HMAC_OFFSET = 4032

# 内存中定位 WCDB/Cipher 相关区域
ANCHOR_PATTERNS = [
    b"com.Tencent.WCDB.Config.Cipher",
    b"MMV1",
    b"WCDB",
    b"Config.Cipher",
    b"cipher_page_size",
]

kernel32 = ctypes.windll.kernel32


def _find_key_info_db() -> Path | None:
    if not DATA_ROOT:
        return None
    login_root = Path(DATA_ROOT) / "all_users" / "login"
    if not login_root.is_dir():
        return None
    for account_dir in login_root.iterdir():
        candidate = account_dir / "key_info.db"
        if candidate.is_file():
            return candidate
    return None


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


def get_db_salt(db_path: str) -> bytes:
    with open(db_path, "rb") as f:
        return f.read(16)


def derive_enc_key(passphrase: bytes, salt: bytes) -> bytes:
    return pbkdf2_hmac("sha512", passphrase, salt, dklen=32, iterations=KDF_ITER)


def try_passphrase(passphrase: bytes, db_path: str) -> bool:
    """验证 passphrase 能否解密数据库第一页"""
    with open(db_path, "rb") as f:
        page1 = f.read(PAGE_SIZE)

    salt = page1[:16]
    enc_key = derive_enc_key(passphrase, salt)
    iv = page1[IV_OFFSET:IV_OFFSET + IV_SIZE]
    encrypted = page1[16:IV_OFFSET]

    try:
        dec = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted)
        return dec[:15] == b"SQLite format 3"
    except Exception:
        return False


def decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    iv = page_data[IV_OFFSET:IV_OFFSET + IV_SIZE]
    if pgno == 1:
        encrypted = page_data[16:IV_OFFSET]
        content = b"SQLite format 3\x00" + AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted)
    else:
        encrypted = page_data[:IV_OFFSET]
        content = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted)
    # 补齐到 PAGE_SIZE
    return content + b"\x00" * (PAGE_SIZE - len(content))


def decrypt_database(src: str, passphrase: bytes, dst: str) -> bool:
    salt = get_db_salt(src)
    enc_key = derive_enc_key(passphrase, salt)

    with open(src, "rb") as f:
        data = f.read()

    page_count = len(data) // PAGE_SIZE
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    with open(dst, "wb") as out:
        for i in range(page_count):
            offset = i * PAGE_SIZE
            page = data[offset:offset + PAGE_SIZE]
            out.write(decrypt_page(enc_key, page, i + 1))
    return True


def copy_and_decrypt(src: str, passphrase: bytes, dst: str) -> bool:
    tmp = dst + ".enc"
    try:
        shutil.copy2(src, tmp)
        return decrypt_database(tmp, passphrase, dst)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def find_weixin_pid() -> int | None:
    from wxlocal.core.subprocess_win import run_silent

    result = run_silent(
        ["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
    )
    best_pid, best_mem = None, 0
    for line in result.stdout.strip().splitlines():
        parts = line.strip('"').split('","')
        if len(parts) >= 5 and parts[0] == "Weixin.exe":
            pid, mem = int(parts[1]), int(parts[4].replace(",", "").replace(" K", ""))
            if mem > best_mem:
                best_pid, best_mem = pid, mem
    return best_pid


def _read_memory(pid: int) -> bytes:
    h = kernel32.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        raise PermissionError(f"无法打开进程 {pid}，请以管理员身份运行")

    chunks = []
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    while kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        rs = mbi.RegionSize
        if mbi.State == 0x1000 and 0 < rs <= 64 * 1024 * 1024 and not (mbi.Protect & 0x101):
            buf = (ctypes.c_char * rs)()
            br = ctypes.c_size_t(0)
            if kernel32.ReadProcessMemory(h, ctypes.c_void_p(mbi.BaseAddress), buf, rs, ctypes.byref(br)):
                chunks.append(bytes(buf[:br.value]))
        nxt = (mbi.BaseAddress or 0) + rs
        if nxt <= addr:
            break
        addr = nxt
    kernel32.CloseHandle(h)
    return b"".join(chunks)


def _collect_passphrase_candidates(memory: bytes, db_path: str) -> list[bytes]:
    """从内存中收集 passphrase 候选（32 字节），优先高置信度来源"""
    candidates: list[bytes] = []
    seen: set[bytes] = set()
    salt = get_db_salt(db_path)

    def add(chunk: bytes):
        if len(chunk) != 32 or chunk in seen or chunk == b"\x00" * 32:
            return
        if chunk.count(0) > 16:  # 太多零字节的跳过
            return
        seen.add(chunk)
        candidates.append(chunk)

    # 1. key_info_data 中的 32 字节块（最高优先级）
    key_info_db = _find_key_info_db()
    if key_info_db:
        try:
            conn = sqlite3.connect(str(key_info_db))
            row = conn.execute("SELECT key_info_data FROM LoginKeyInfoTable LIMIT 1").fetchone()
            conn.close()
            if row:
                blob = row[0] if isinstance(row[0], bytes) else bytes.fromhex(row[0])
                for i in range(0, len(blob) - 31, 4):
                    add(blob[i:i + 32])
        except Exception:
            pass

    # 2. 锚点字符串附近 ±128 字节（每 4 字节采样）
    for anchor in ANCHOR_PATTERNS:
        pos = 0
        while True:
            idx = memory.find(anchor, pos)
            if idx == -1:
                break
            for offset in range(-128, 129, 4):
                start = idx + offset
                if 0 <= start <= len(memory) - 32:
                    add(bytes(memory[start:start + 32]))
            pos = idx + 1

    # 3. salt 附近 ±64 字节
    pos = 0
    while True:
        idx = memory.find(salt, pos)
        if idx == -1:
            break
        for off in range(-64, 65, 4):
            start = idx + off
            if 0 <= start <= len(memory) - 32:
                add(bytes(memory[start:start + 32]))
        pos = idx + 1

    return candidates[:200]  # 限制数量


def scan_passphrase(pid: int, db_files: list[str]) -> bytes | None:
    """扫描并返回有效的 32 字节 passphrase"""
    memory = _read_memory(pid)
    # 用 message 库做验证（最大最可能有数据）
    test_db = next((f for f in db_files if "message_0.db" in f), db_files[0] if db_files else None)
    if not test_db:
        return None

    tmp = tempfile.mktemp(suffix=".db")
    shutil.copy2(test_db, tmp)

    try:
        for pp in _collect_passphrase_candidates(memory, test_db):
            if try_passphrase(pp, tmp):
                return pp
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return None


def scan_keys(pid: int, db_files: list[str]) -> dict[str, str]:
    """兼容接口：返回 {db_path: passphrase_hex}"""
    pp = scan_passphrase(pid, db_files)
    if not pp:
        return {}
    hex_pp = pp.hex()
    return {db: hex_pp for db in db_files}
