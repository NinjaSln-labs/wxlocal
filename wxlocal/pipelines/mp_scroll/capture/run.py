"""启动微信订阅号抓包代理（mitmproxy）。

环境变量:
  MP_CAPTURE_PORT=8848
  MP_CAPTURE_UPSTREAM=http://127.0.0.1:6696   # 留空则直连
  MP_CAPTURE_RAW=1
  MP_CAPTURE_VERBOSE=1
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from wxlocal.config._root import PROJECT_ROOT
from wxlocal.config.paths import MP_CAPTURE_KB

ADDON = Path(__file__).resolve().parent / "addon.py"
PORT = os.environ.get("MP_CAPTURE_PORT", "8848")
UPSTREAM = os.environ.get("MP_CAPTURE_UPSTREAM", "http://127.0.0.1:6696").strip()


def main() -> None:
    mitmdump = shutil.which("mitmdump")
    if not mitmdump:
        venv_mitm = PROJECT_ROOT / ".venv" / "Scripts" / "mitmdump.exe"
        mitmdump = str(venv_mitm) if venv_mitm.is_file() else None
    if not mitmdump:
        print("未找到 mitmdump。请先安装: pip install mitmproxy")
        sys.exit(1)

    cmd = [
        mitmdump,
        "-s",
        str(ADDON),
        "-p",
        PORT,
        "--set",
        "block_global=false",
        "--set",
        "ssl_insecure=true",
    ]
    if UPSTREAM:
        cmd.extend(["--mode", f"upstream:{UPSTREAM}"])

    print("=" * 60)
    print("微信 PC 订阅号抓包代理")
    print(f"  监听: 127.0.0.1:{PORT}")
    print(f"  上游: {UPSTREAM or '(直连)'}")
    print(f"  语料: {MP_CAPTURE_KB}")
    print()
    print("下一步:")
    print("  1) 安装 mitmproxy 证书 (首次): mitmdump 后访问 http://mitm.it")
    print("  2) 让 Weixin.exe 走代理 127.0.0.1:" + PORT)
    print("     - 系统代理，或 Proxifier 规则指向 Weixin.exe")
    print("  3) PC 微信打开「订阅号」，浏览/点开文章")
    print("  4) 另开终端: python -m wxlocal.export.mp_capture_export")
    print("=" * 60)

    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print("\n已停止抓包。")


if __name__ == "__main__":
    main()
