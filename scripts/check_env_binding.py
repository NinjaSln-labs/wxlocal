"""T0: assert path/config constants bind from a temp .env in a fresh process.

Catches R5-class bugs where load_env() runs after import-time os.environ reads.
No WeChat process required — always run in CI and verify.ps1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix="wxlocal_t0_"))
    env_file = td / ".env"
    kb = td / "kb"
    env_file.write_text(
        "\n".join(
            [
                "WECHAT_WATCH_CONTACT=VerifyProbe",
                f"WECHAT_KB_ROOT={kb.as_posix()}",
                "WECHAT_DATA_ROOT=D:/verify/xwechat_files",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["WXLOCAL_ENV_FILE"] = str(env_file)
    for key in (
        "WECHAT_WATCH_CONTACT",
        "WECHAT_KB_ROOT",
        "WECHAT_DATA_ROOT",
        "WECHAT_RADIUM_PROFILES",
    ):
        env.pop(key, None)

    probe = (
        "import json, os\n"
        "for k in ('WECHAT_WATCH_CONTACT','WECHAT_KB_ROOT','WECHAT_DATA_ROOT','WECHAT_RADIUM_PROFILES'):\n"
        "    os.environ.pop(k, None)\n"
        "from wxlocal.config import paths, config\n"
        "print(json.dumps({"
        "'c': paths.WATCH_CONTACT, "
        "'kb': str(paths.KB_ROOT), "
        "'d': config.DATA_ROOT"
        "}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "env probe failed\n")
        return result.returncode or 1

    data = json.loads(result.stdout.strip().splitlines()[-1])
    if data["c"] != "VerifyProbe":
        sys.stderr.write(f"WATCH_CONTACT not bound: {data}\n")
        return 1
    if Path(data["kb"]) != kb:
        sys.stderr.write(f"KB_ROOT not bound: {data}\n")
        return 1
    if data["d"].replace("\\", "/") != "D:/verify/xwechat_files":
        sys.stderr.write(f"DATA_ROOT not bound: {data}\n")
        return 1
    print(f"T0 OK contact={data['c']} kb={data['kb']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
