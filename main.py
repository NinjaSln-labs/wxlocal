"""微信聊天记录读取 - 主入口"""
import argparse
import glob
import os
import sys

from config import DATA_ROOT, DECRYPTED_DIR, OUTPUT_DIR
from decrypt_db import copy_and_decrypt
from read_messages import export_json, read_messages, read_sessions
from scan_keys_v41 import find_weixin_pid, scan_keys, scan_passphrase


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


def main():
    parser = argparse.ArgumentParser(description="从微信 PC 4.x 读取聊天记录")
    parser.add_argument("--data-root", default=DATA_ROOT)
    parser.add_argument("--limit", type=int, default=50, help="读取消息条数")
    parser.add_argument("--talker", default="", help="过滤指定联系人 wxid")
    parser.add_argument("--log", default=os.path.join(OUTPUT_DIR, "run.log"), help="日志文件路径")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_lines = []

    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("[*] 微信聊天记录读取工具 (Python)")
    log(f"[*] 数据目录: {args.data_root}")

    pid = find_weixin_pid()
    if not pid:
        log("[!] 未找到运行中的 Weixin.exe，请先登录微信")
        _write_log(args.log, log_lines)
        sys.exit(1)
    log(f"[+] 微信进程 PID={pid}")

    user_dir = find_user_dir(args.data_root)
    db_storage = os.path.join(user_dir, "db_storage")
    log(f"[+] 用户目录: {user_dir}")

    db_files = collect_db_files(db_storage)
    log(f"[*] 发现 {len(db_files)} 个数据库")

    log("[*] 扫描进程内存提取密钥（微信 4.1+ passphrase 模式）...")
    try:
        passphrase = scan_passphrase(pid, db_files)
        if passphrase:
            keys = {db: passphrase.hex() for db in db_files}
            log(f"[+] 找到 passphrase: {passphrase.hex()[:16]}...")
        else:
            keys = {}
    except PermissionError as e:
        log(f"[!] {e}")
        log("[!] 请以管理员身份运行: 右键 PowerShell -> 以管理员身份运行")
        _write_log(args.log, log_lines)
        sys.exit(1)

    log(f"[+] 提取到 {len(keys)} 个密钥")
    if not keys:
        log("[!] 未能提取密钥，请确保微信已登录且以管理员身份运行")
        _write_log(args.log, log_lines)
        sys.exit(1)

    os.makedirs(DECRYPTED_DIR, exist_ok=True)
    decrypted = {}
    for src in db_files:
        rel = os.path.relpath(src, db_storage)
        dst = os.path.join(DECRYPTED_DIR, rel)
        pp_hex = keys.get(src, "")
        if not pp_hex:
            continue
        log(f"[*] 解密: {rel}")
        if copy_and_decrypt(src, pp_hex, dst):
            decrypted[rel] = dst
            log(f"    -> 成功")
        else:
            log(f"    -> 失败")

    # 读取会话
    session_path = next((v for k, v in decrypted.items() if "session" in k and k.endswith("session.db")), None)
    if session_path:
        log("\n========== 会话列表 ==========")
        sessions = read_sessions(session_path)
        for s in sessions[:10]:
            log(str(s))

    # 读取消息
    msg_path = next((v for k, v in decrypted.items() if "message" in k and "message_" in k), None)
    if not msg_path:
        log("[!] 未找到解密后的消息数据库")
        _write_log(args.log, log_lines)
        sys.exit(1)

    log("\n========== 聊天记录 ==========")
    messages = read_messages(msg_path, limit=args.limit, talker=args.talker)
    for msg in messages:
        log(f"[{msg['time']}] {msg['sender']}: {msg['content'][:200]}")

    export_path = os.path.join(OUTPUT_DIR, "messages.json")
    export_json(messages, export_path)
    log(f"\n[+] 已导出 {len(messages)} 条消息到 {export_path}")
    log(f"[+] 解密数据库目录: {DECRYPTED_DIR}")
    _write_log(args.log, log_lines)


def _write_log(path: str, lines: list[str]):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
