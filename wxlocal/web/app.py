"""WeChat chat history Web UI."""
import json
import os

from flask import Flask, jsonify, render_template, request, send_file

from wxlocal.config._root import PROJECT_ROOT
from wxlocal.config.config import OUTPUT_DIR
from wxlocal.web.service import (
    auto_scan,
    decrypt_all,
    decrypt_from_text,
    get_messages,
    get_sessions,
    get_state,
    init_paths,
)

app = Flask(__name__, template_folder=str(PROJECT_ROOT / "templates"))
app.config["JSON_AS_ASCII"] = False


@app.route("/")
def index():
    state = get_state()
    try:
        init_paths()
        ready = bool(state.db_storage)
    except FileNotFoundError as e:
        ready = False
        state.last_error = str(e)
    return render_template(
        "index.html",
        ready=ready,
        data_root=state.data_root,
        decrypted=bool(state.decrypted),
        last_error=state.last_error,
        last_info=state.last_info,
    )


@app.route("/api/status")
def api_status():
    state = get_state()
    return jsonify({
        "ready": bool(state.db_storage),
        "decrypted": bool(state.decrypted),
        "db_count": len(state.decrypted),
        "last_error": state.last_error,
        "last_info": state.last_info,
    })


@app.route("/api/decrypt", methods=["POST"])
def api_decrypt():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "") or data.get("passphrase_hex", "")
    passphrase_hex = data.get("passphrase_hex", "")

    if passphrase_hex:
        result = decrypt_all(passphrase_hex.strip())
    elif text:
        result = decrypt_from_text(text)
    else:
        return jsonify({"ok": False, "error": "请粘贴密钥文本"}), 400

    state = get_state()
    if not result:
        return jsonify({"ok": False, "error": state.last_error or "解密失败"}), 400

    return jsonify({
        "ok": True,
        "count": len(result),
        "info": state.last_info,
    })


@app.route("/api/auto-scan", methods=["POST"])
def api_auto_scan():
    pp_hex = auto_scan()
    state = get_state()
    if not pp_hex:
        return jsonify({"ok": False, "error": state.last_error}), 400

    result = decrypt_all(pp_hex)
    return jsonify({
        "ok": True,
        "passphrase_hex": pp_hex,
        "count": len(result),
        "info": state.last_info,
    })


@app.route("/api/sessions")
def api_sessions():
    limit = request.args.get("limit", 50, type=int)
    sessions = get_sessions(limit=limit)
    return jsonify({"sessions": sessions})


@app.route("/api/messages")
def api_messages():
    limit = request.args.get("limit", 100, type=int)
    talker = request.args.get("talker", "")
    keyword = request.args.get("keyword", "")
    messages = get_messages(limit=limit, talker=talker, keyword=keyword)
    return jsonify({"messages": messages, "count": len(messages)})


@app.route("/api/export")
def api_export():
    messages = get_messages(limit=1000)
    path = os.path.join(OUTPUT_DIR, "messages_export.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    return send_file(path, as_attachment=True, download_name="messages.json")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    try:
        init_paths()
        print(f"[*] 数据目录: {get_state().data_root}")
        print(f"[*] 用户目录: {get_state().user_dir}")
    except FileNotFoundError as e:
        print(f"[!] {e}")

    print(f"[+] Web 服务: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
