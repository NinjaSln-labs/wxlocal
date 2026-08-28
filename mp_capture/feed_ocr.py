"""OCR 订阅号推荐流可见卡片标题（补 IDB 不落盘的推荐卡）。"""
from __future__ import annotations

import hashlib
import ctypes
import os
import re
from pathlib import Path

from wxlocal.config.paths import MP_SCROLL_OCR_DIR, ensure_mp_scroll_dirs

OCR_DIR = MP_SCROLL_OCR_DIR
_OCR_ENGINE = None
MIN_TITLE_LEN = 8
NOISE_RE = re.compile(
    r"^(订阅|订阅号|推荐|搜索|全部|关注|朋友|发现|我|微信|服务|视频号|\d{1,2}:\d{2})$"
)


def _get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _ocr_image(path: Path) -> str:
    try:
        result, _ = _get_ocr_engine()(str(path))
    except ImportError:
        return ""
    if not result:
        return ""
    lines = [str(row[1]).strip() for row in result if len(row) >= 2 and row[1]]
    return "\n".join(lines)


DEV_HINTS = ("Agent", "AI", "GitHub", "开源", "Claude", "MCP", "Skill", "渗透", "代码库", "OCR")


def _weixin_pids() -> set[int]:
    pids: set[int] = set()
    try:
        from subprocess_win import run_silent

        out = run_silent(
            ["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            errors="ignore",
        ).stdout
        for line in out.splitlines():
            if "Weixin.exe" not in line:
                continue
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 2 and parts[1].isdigit():
                pids.add(int(parts[1]))
    except Exception:
        pass
    return pids


def _find_wechat_hwnd() -> int | None:
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    user32 = ctypes.windll.user32
    pids = _weixin_pids()
    if not pids:
        return None

    candidates: list[tuple[int, int]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in pids:
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
        if area < 200 * 200:
            return True
        candidates.append((area, int(hwnd)))
        return True

    user32.EnumWindows(callback, 0)
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    """裁切微信窗口内的订阅号列表区（相对窗口比例，与屏幕左右无关）。"""
    raw = os.environ.get("MP_SCROLL_OCR_CROP", "0.08,0.10,0.98,0.92")
    try:
        l, t, r, b = (float(x) for x in raw.split(","))
    except ValueError:
        l, t, r, b = 0.08, 0.10, 0.98, 0.92
    return (
        int(width * l),
        int(height * t),
        int(width * r),
        int(height * b),
    )


def _capture_hwnd(hwnd: int, out: Path) -> bool:
    """PrintWindow 后台截图，避免 ImageGrab 闪黑框。"""
    try:
        from ctypes import wintypes

        from PIL import Image
    except ImportError:
        return False

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    width, height = right - left, bottom - top
    if width < 200 or height < 200:
        return False

    hwnd_dc = user32.GetWindowDC(hwnd)
    if not hwnd_dc:
        return False
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    full_bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    if not mem_dc or not full_bmp:
        user32.ReleaseDC(hwnd, hwnd_dc)
        return False

    old = gdi32.SelectObject(mem_dc, full_bmp)
    # PW_CLIENTONLY(1) | PW_RENDERFULLCONTENT(2)：后台抓子窗口，避免闪黑框
    PW_FLAGS = 3
    if not user32.PrintWindow(hwnd, mem_dc, PW_FLAGS):
        return False

    crop_box = _crop_box(width, height)
    cw, ch = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
    crop_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    crop_bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, cw, ch)
    gdi32.SelectObject(crop_dc, crop_bmp)
    gdi32.BitBlt(crop_dc, 0, 0, cw, ch, mem_dc, crop_box[0], crop_box[1], 0x00CC0020)  # SRCCOPY

    bmpinfo = BITMAPINFO()
    bmpinfo.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmpinfo.bmiHeader.biWidth = cw
    bmpinfo.bmiHeader.biHeight = -ch
    bmpinfo.bmiHeader.biPlanes = 1
    bmpinfo.bmiHeader.biBitCount = 32
    bmpinfo.bmiHeader.biCompression = 0  # BI_RGB
    buf = ctypes.create_string_buffer(cw * ch * 4)
    gdi32.GetDIBits(crop_dc, crop_bmp, 0, ch, buf, ctypes.byref(bmpinfo), 0)
    img = Image.frombuffer("RGBA", (cw, ch), buf, "raw", "BGRA", 0, 1).convert("RGB")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

    gdi32.SelectObject(mem_dc, old)
    gdi32.DeleteObject(full_bmp)
    gdi32.DeleteObject(crop_bmp)
    gdi32.DeleteDC(mem_dc)
    gdi32.DeleteDC(crop_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    return True


def is_plausible_feed_title(line: str) -> bool:
    cn = len(re.findall(r"[\u4e00-\u9fff]", line))
    if cn >= 4:
        return True
    if cn >= 2 and any(h in line for h in DEV_HINTS):
        return True
    return False


def extract_titles_from_text(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < MIN_TITLE_LEN:
            continue
        if NOISE_RE.match(line):
            continue
        if not is_plausible_feed_title(line):
            continue
        if re.search(r"\.py\b|Linter|Cursor|registry\.py", line, re.I):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(line)
    return titles


def scan_visible_feed(*, save_shot: bool | None = None) -> dict:
    """截微信窗口 OCR 可见标题。失败时返回空列表，不抛错。"""
    enabled = os.environ.get("MP_SCROLL_OCR", "0") not in ("0", "false", "False")
    if not enabled:
        return {"enabled": False, "titles": [], "shot": ""}

    hwnd = _find_wechat_hwnd()
    if not hwnd:
        return {"enabled": True, "titles": [], "shot": "", "error": "wechat_window_not_found"}

    OCR_DIR.mkdir(parents=True, exist_ok=True)
    ensure_mp_scroll_dirs()
    shot = OCR_DIR / "latest_feed.png"
    keep = save_shot if save_shot is not None else os.environ.get("MP_SCROLL_OCR_SAVE", "0") in ("1", "true")
    if not _capture_hwnd(hwnd, shot):
        return {"enabled": True, "titles": [], "shot": "", "error": "capture_failed"}

    text = _ocr_image(shot)
    titles = extract_titles_from_text(text)
    if not keep:
        try:
            shot.unlink(missing_ok=True)
        except OSError:
            pass
    return {
        "enabled": True,
        "titles": titles,
        "shot": str(shot) if keep and shot.is_file() else "",
        "raw_len": len(text),
    }


def title_registry_key(title: str) -> str:
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    return f"ocr://feed/{digest}"
