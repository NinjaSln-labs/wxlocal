"""解析用户粘贴的密钥文本"""
import re


def parse_key_input(text: str) -> tuple[bytes | None, str]:
    """
    从粘贴文本中解析密钥。
    返回 (passphrase_bytes, key_type)
    key_type: 'passphrase' | 'raw_key' | ''
    """
    if not text or not text.strip():
        return None, ""

    cleaned = text.strip()

    # x'<96hex>' 格式（旧版 4.0 或工具输出）
    m = re.search(r"x'([0-9a-fA-F]{96})'", cleaned, re.IGNORECASE)
    if m:
        hex96 = m.group(1).lower()
        # 前 64 hex = enc_key, 后 32 = salt；4.1+ 用前 32 字节作为 passphrase 尝试
        return bytes.fromhex(hex96[:64]), "raw_key"

    # 提取所有连续 hex
    hex_chunks = re.findall(r"[0-9a-fA-F]{32,}", cleaned)
    for chunk in hex_chunks:
        chunk = chunk.lower()
        if len(chunk) == 64:
            return bytes.fromhex(chunk), "passphrase"
        if len(chunk) == 96:
            return bytes.fromhex(chunk[:64]), "raw_key"
        if len(chunk) > 64:
            # 取前 64 字符
            return bytes.fromhex(chunk[:64]), "passphrase"

    # 纯 hex（无其他字符）
    pure = re.sub(r"[^0-9a-fA-F]", "", cleaned).lower()
    if len(pure) >= 64:
        return bytes.fromhex(pure[:64]), "passphrase"
    if len(pure) >= 32:
        return bytes.fromhex(pure[:32].ljust(64, "0")[:64]), "passphrase"

    return None, ""
