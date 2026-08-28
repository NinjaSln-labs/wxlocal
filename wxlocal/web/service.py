"""WeChat decrypt and read service layer."""
import os
from dataclasses import dataclass, field

from wxlocal._legacy import bootstrap_legacy_imports

bootstrap_legacy_imports()

from decrypt_db import decrypt_with_fallback
from key_parser import parse_key_input
from read_messages import read_messages, read_sessions
from scan_keys_v41 import find_weixin_pid, scan_passphrase, try_passphrase

from wxlocal.config.config import DATA_ROOT, DECRYPTED_DIR, OUTPUT_DIR


@dataclass
class AppState:
    data_root: str = DATA_ROOT
    user_dir: str = ""
    db_storage: str = ""
    passphrase_hex: str = ""
    decrypted: dict = field(default_factory=dict)
    last_error: str = ""
    last_info: str = ""


_state = AppState()


def get_state() -> AppState:
    return _state


def find_user_dir(data_root: str) -> str:
    for name in os.listdir(data_root):
        full = os.path.join(data_root, name)
        if os.path.isdir(full) and name not in ("all_users", "Backup"):
            db_storage = os.path.join(full, "db_storage")
            if os.path.isdir(db_storage):
                return full
    raise FileNotFoundError(f"未找到用户数据目录: {data_root}")


def collect_db_files(db_storage: str) -> list[str]:
    files = []
    for root, _, names in os.walk(db_storage):
        for name in names:
            if name.endswith(".db") and ".db-" not in name:
                files.append(os.path.join(root, name))
    return files


def init_paths(data_root: str | None = None):
    state = get_state()
    state.data_root = data_root or DATA_ROOT
    state.user_dir = find_user_dir(state.data_root)
    state.db_storage = os.path.join(state.user_dir, "db_storage")
    return state


def validate_passphrase(passphrase: bytes) -> bool:
    state = get_state()
    if not state.db_storage:
        init_paths()
    db_files = collect_db_files(state.db_storage)
    test_db = next((f for f in db_files if "message_0.db" in f), None)
    if not test_db:
        return False
    import shutil
    import tempfile

    tmp = tempfile.mktemp(suffix=".db")
    shutil.copy2(test_db, tmp)
    try:
        return try_passphrase(passphrase, tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def decrypt_all(passphrase_hex: str) -> dict:
    """Decrypt all databases; return {rel_path: abs_path}."""
    state = get_state()
    if not state.db_storage:
        init_paths()

    try:
        passphrase = bytes.fromhex(passphrase_hex)
    except ValueError:
        state.last_error = "密钥格式无效，需要 64 位十六进制"
        return {}

    if not validate_passphrase(passphrase):
        state.last_error = "密钥验证失败，无法解密数据库"
        return {}

    os.makedirs(DECRYPTED_DIR, exist_ok=True)
    db_files = collect_db_files(state.db_storage)
    decrypted = {}
    ok_count = 0

    for src in db_files:
        rel = os.path.relpath(src, state.db_storage)
        dst = os.path.join(DECRYPTED_DIR, rel)
        if decrypt_with_fallback(src, passphrase_hex, dst):
            decrypted[rel] = dst
            ok_count += 1

    state.passphrase_hex = passphrase_hex
    state.decrypted = decrypted
    state.last_error = ""
    state.last_info = f"成功解密 {ok_count}/{len(db_files)} 个数据库"
    return decrypted


def decrypt_from_text(text: str) -> dict:
    """Parse pasted key text and decrypt."""
    passphrase, key_type = parse_key_input(text)
    if not passphrase:
        get_state().last_error = "无法从文本中解析密钥，请粘贴 64 位 hex 或 x'...' 格式"
        return {}
    pp = passphrase[:32] if len(passphrase) >= 32 else passphrase
    return decrypt_all(pp.hex())


def auto_scan() -> str:
    """Scan process memory; return passphrase hex or empty."""
    state = get_state()
    if not state.db_storage:
        init_paths()

    pid = find_weixin_pid()
    if not pid:
        state.last_error = "未找到运行中的微信，请先登录"
        return ""

    db_files = collect_db_files(state.db_storage)
    try:
        pp = scan_passphrase(pid, db_files)
    except PermissionError:
        state.last_error = "需要管理员权限才能扫描内存，请以管理员身份运行 Web 服务"
        return ""

    if not pp:
        state.last_error = "未能从内存提取密钥，请手动粘贴密钥"
        return ""

    state.last_info = f"自动扫描成功: {pp.hex()[:16]}..."
    return pp.hex()


def get_session_db() -> str | None:
    state = get_state()
    return next(
        (v for k, v in state.decrypted.items() if "session" in k and k.endswith("session.db")),
        None,
    )


def get_message_db() -> str | None:
    state = get_state()
    return next(
        (v for k, v in state.decrypted.items() if "message" in k and "message_" in k),
        None,
    )


def get_sessions(limit: int = 50) -> list[dict]:
    path = get_session_db()
    if not path:
        return []
    return read_sessions(path, limit=limit)


def get_messages(limit: int = 100, talker: str = "", keyword: str = "") -> list[dict]:
    path = get_message_db()
    if not path:
        return []
    msgs = read_messages(path, limit=limit * 3 if keyword else limit, talker=talker)
    if keyword:
        kw = keyword.lower()
        msgs = [m for m in msgs if kw in str(m.get("content", "")).lower() or kw in str(m.get("talker", "")).lower()]
    return msgs[:limit]
