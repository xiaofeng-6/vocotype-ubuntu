"""Text injection: Windows (SendInput) 与 Linux/macOS。

推荐 ``method=paste``: 把**与转写回调相同**的整段 str 写入剪贴板,再模拟粘贴快捷键,不逐字模拟(减少叠字)。
``paste_hotkey=dual``（默认）只写一次剪贴板,再模拟 **Ctrl+Shift+V**（终端常见）; 普通文本框可改 ``ctrl+v`` 或 ``hybrid``（Shift+Insert）。
仍失败时可试 unicode/type 等回退。
"""

from __future__ import annotations

import logging
from typing import Optional
import os
import shutil
import subprocess
import sys
import threading
import time

logger = logging.getLogger(__name__)

# 先粘贴再延迟恢复旧剪贴板(秒)。过短会贴成旧内容；与 Timer 二选一,这里用于读剪贴板完成前不覆盖
_CLIPBOARD_PASTE_SETTLE_S = 0.12
# 用 Timer 在粘贴之后再恢复剪贴板(秒)
_CLIPBOARD_RESTORE_DELAY_S = 0.55

# type_text 一次调用里 pynput 逐字间隔（由 type_text 入口设置，供非 Windows 的 _type_with_unicode_pynput 读取）
_pynput_inter_char_delay_s: float = 0.0

# 若连续快速转写,取消尚未触发的旧「恢复剪贴板」定时器,避免与下一次粘贴打架
_pending_clipboard_restore_timer: Optional[threading.Timer] = None

# ---------------------------------------------------------------------------
# Windows: ctypes + SendInput
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wintypes

    SendInput = ctypes.windll.user32.SendInput
    GetMessageExtraInfo = ctypes.windll.user32.GetMessageExtraInfo

    _INPUT_KEYBOARD = 1
    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_UNICODE = 0x0004
    _VK_CONTROL = 0x11
    _VK_SHIFT = 0x10
    _VK_INSERT = 0x2D
    _VK_V = 0x56

    if hasattr(wintypes, "ULONG_PTR"):
        _ULONG_PTR = wintypes.ULONG_PTR  # type: ignore[attr-defined]
    else:
        if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_uint64):
            _ULONG_PTR = ctypes.c_uint64
        else:
            _ULONG_PTR = ctypes.c_uint32

    class _KeyboardInput(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", _ULONG_PTR),
        ]

    class _InputUnion(ctypes.Union):
        _fields_ = [("ki", _KeyboardInput)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]

    def _emit_unicode_char(char: str) -> bool:
        code_point = ord(char)
        input_array_type = _INPUT * 2
        inputs = input_array_type(
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=0,
                        wScan=code_point,
                        dwFlags=_KEYEVENTF_UNICODE,
                        time=0,
                        dwExtraInfo=GetMessageExtraInfo(),
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=0,
                        wScan=code_point,
                        dwFlags=_KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=GetMessageExtraInfo(),
                    )
                ),
            ),
        )
        pointer = ctypes.byref(inputs[0])
        sent = SendInput(len(inputs), pointer, ctypes.sizeof(_INPUT))
        if sent != len(inputs):
            logger.warning("SendInput 发送字符失败，char=%s，返回值=%s", char, sent)
            return False
        return True

    def _type_with_unicode_line(payload: str) -> bool:
        success = True
        for char in payload:
            if not _emit_unicode_char(char):
                success = False
                break
        return success

    def _win_emit_ctrl_v() -> bool:
        input_array_type = _INPUT * 4
        extra = GetMessageExtraInfo()
        inputs = input_array_type(
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_CONTROL,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_V,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_V,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_CONTROL,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
        )
        pointer = ctypes.byref(inputs[0])
        sent = SendInput(len(inputs), pointer, ctypes.sizeof(_INPUT))
        if sent != len(inputs):
            logger.warning("SendInput Ctrl+V 失败，返回值=%s", sent)
            sent_retry = SendInput(len(inputs), pointer, ctypes.sizeof(_INPUT))
            if sent_retry != len(inputs):
                logger.warning("SendInput Ctrl+V 第二次重试失败，返回值=%s", sent_retry)
                return False
        return True

    def _win_emit_ctrl_shift_v() -> bool:
        input_array_type = _INPUT * 6
        extra = GetMessageExtraInfo()
        inputs = input_array_type(
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_CONTROL,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_SHIFT,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_V,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_V,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_SHIFT,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_CONTROL,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
        )
        pointer = ctypes.byref(inputs[0])
        sent = SendInput(len(inputs), pointer, ctypes.sizeof(_INPUT))
        if sent != len(inputs):
            logger.warning("SendInput Ctrl+Shift+V 失败，返回值=%s", sent)
            return False
        return True

    def _win_emit_shift_insert() -> bool:
        input_array_type = _INPUT * 4
        extra = GetMessageExtraInfo()
        inputs = input_array_type(
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_SHIFT,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_INSERT,
                        wScan=0,
                        dwFlags=0,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_INSERT,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
            _INPUT(
                type=_INPUT_KEYBOARD,
                union=_InputUnion(
                    ki=_KeyboardInput(
                        wVk=_VK_SHIFT,
                        wScan=0,
                        dwFlags=_KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra,
                    )
                ),
            ),
        )
        pointer = ctypes.byref(inputs[0])
        sent = SendInput(len(inputs), pointer, ctypes.sizeof(_INPUT))
        if sent != len(inputs):
            logger.warning("SendInput Shift+Insert 失败，返回值=%s", sent)
            return False
        return True

    def _emit_paste_hotkey(hotkey: str) -> bool:
        hk = _normalize_paste_hotkey(hotkey)
        if hk == "shift+insert":
            return _win_emit_shift_insert()
        if hk == "ctrl+shift+v":
            return _win_emit_ctrl_shift_v()
        if hk == "ctrl+v":
            return _win_emit_ctrl_v()
        logger.warning("不支持的 paste_hotkey %r，改用 ctrl+v", hotkey)
        return _win_emit_ctrl_v()

# ---------------------------------------------------------------------------
# Linux / macOS: pynput，可选 keyboard
# ---------------------------------------------------------------------------
else:

    def _emit_paste_subprocess(cmd: list[str]) -> bool:
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                timeout=3,
                check=False,
            )
            if r.returncode != 0:
                logger.debug(
                    "subprocess 粘贴快捷键 非零退出: %s rc=%s stderr=%s",
                    cmd,
                    r.returncode,
                    r.stderr[:200] if r.stderr else b"",
                )
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("subprocess 粘贴快捷键失败 %s: %s", cmd, exc)
            return False

    def _emit_paste_pynput(hotkey: str) -> bool:
        try:
            from pynput.keyboard import Controller, Key

            c = Controller()
            if hotkey == "ctrl+shift+v":
                c.press(Key.ctrl)
                c.press(Key.shift)
                c.press("v")
                c.release("v")
                c.release(Key.shift)
                c.release(Key.ctrl)
            elif hotkey == "shift+insert":
                c.press(Key.shift)
                c.press(Key.insert)
                c.release(Key.insert)
                c.release(Key.shift)
            else:
                c.press(Key.ctrl)
                c.press("v")
                c.release("v")
                c.release(Key.ctrl)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("pynput %s 失败: %s", hotkey, exc)
            return False

    def _emit_paste_keyboard_lib(hotkey: str) -> bool:
        try:
            import keyboard

            keyboard.send(hotkey)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("keyboard %s 失败: %s", hotkey, exc)
            return False

    def _emit_paste_hotkey(hotkey: str) -> bool:
        hk = _normalize_paste_hotkey(hotkey)
        if hk not in ("ctrl+v", "ctrl+shift+v", "shift+insert"):
            logger.warning("不支持的 paste_hotkey %r，改用 ctrl+v", hotkey)
            hk = "ctrl+v"
        if _emit_paste_pynput(hk):
            return True
        if _emit_paste_keyboard_lib(hk):
            return True
        if hk == "shift+insert":
            xdotool_arg = "shift+Insert"
            wtype_cmd = ["wtype", "-M", "shift", "Insert"]
        elif hk == "ctrl+shift+v":
            xdotool_arg = "ctrl+shift+v"
            wtype_cmd = ["wtype", "-M", "ctrl", "-M", "shift", "v"]
        else:
            xdotool_arg = "ctrl+v"
            wtype_cmd = ["wtype", "-M", "ctrl", "v"]
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
            if _emit_paste_subprocess(wtype_cmd):
                return True
        if os.environ.get("DISPLAY") and shutil.which("xdotool"):
            if _emit_paste_subprocess(["xdotool", "key", "--clearmodifiers", xdotool_arg]):
                return True
        if shutil.which("wtype"):
            if _emit_paste_subprocess(wtype_cmd):
                return True
        return False

    def _type_with_unicode_pynput(payload: str) -> bool:
        global _pynput_inter_char_delay_s
        try:
            from pynput.keyboard import Controller

            c = Controller()
            delay = float(_pynput_inter_char_delay_s)
            if delay <= 0:
                c.type(payload)
            else:
                # 整段 type 在 Linux+部分输入法 下易叠字；逐字+短隔更稳
                for ch in payload:
                    c.type(ch)
                    time.sleep(delay)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("pynput 逐字/整段输入失败: %s", exc)
            return False

    def _type_with_unicode_line(payload: str) -> bool:
        if _type_with_unicode_pynput(payload):
            return True
        if _type_with_keyboard(payload):
            return True
        for char in payload:
            if not _emit_unicode_char(char):
                return False
        return True

    def _emit_unicode_char(char: str) -> bool:
        """Linux 上逐字符回退：尽量用 pynput 单字输入。"""
        return _type_with_unicode_pynput(char) or _type_with_keyboard(char)


# ---------------------------------------------------------------------------
# 共用
# ---------------------------------------------------------------------------


def _normalize_paste_hotkey(hotkey: str) -> str:
    """规范化粘贴快捷键字符串（与 keyboard 库组合键写法一致）。"""
    s = (hotkey or "ctrl+v").strip().lower().replace(" ", "")
    if s in ("ctrl+v", "control+v"):
        return "ctrl+v"
    if s in ("ctrl+shift+v", "control+shift+v"):
        return "ctrl+shift+v"
    if s in ("shift+insert", "shift+ins"):
        return "shift+insert"
    return s


def _type_with_keyboard(payload: str) -> bool:
    try:
        import keyboard

        keyboard.write(payload, delay=0)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("keyboard.write 失败: %r", exc)
        return False


def _clipboard_snapshot() -> Optional[str]:
    """读取当前剪贴板文本；失败返回 None。"""
    try:
        import pyperclip

        return str(pyperclip.paste())
    except Exception:  # noqa: BLE001
        pass
    if sys.platform == "linux":
        try:
            if shutil.which("xclip"):
                out = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
                if out.returncode == 0:
                    return out.stdout.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        try:
            if shutil.which("wl-paste"):
                out = subprocess.run(
                    ["wl-paste", "-n"],
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
                if out.returncode == 0:
                    return out.stdout.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            if out.returncode == 0:
                return out.stdout.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    return None


def _clipboard_set_text(text: str) -> bool:
    """写入系统剪贴板；成功返回 True。"""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("pyperclip.copy 不可用或失败: %s", exc)

    data = text.encode("utf-8")
    if sys.platform == "linux":
        try:
            if shutil.which("xclip"):
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=data,
                    timeout=5,
                    check=True,
                    capture_output=True,
                )
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("xclip 写入剪贴板失败: %s", exc)
        try:
            if shutil.which("wl-copy"):
                subprocess.run(
                    ["wl-copy"],
                    input=data,
                    timeout=5,
                    check=True,
                    capture_output=True,
                )
                return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("wl-copy 写入剪贴板失败: %s", exc)
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["pbcopy"],
                input=data,
                timeout=5,
                check=True,
                capture_output=True,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("pbcopy 失败: %s", exc)
    return False


def _restore_clipboard_content(prev: object) -> None:
    if prev is None:
        return
    try:
        s = prev if isinstance(prev, str) else str(prev)
    except Exception:  # noqa: BLE001
        return
    if _clipboard_set_text(s):
        return
    try:
        import pyperclip

        pyperclip.copy(s)
    except Exception:  # noqa: BLE001
        pass


def _try_clipboard_injection(payload: str, paste_hotkey: str = "dual") -> bool:
    """将 payload 原样放入剪贴板,再模拟粘贴快捷键,整段进框; 不逐字键入(避免叠字).

    恢复旧剪贴板**延后**到 Timer(异步), 给目标应用足够时间从剪贴板取转写内容。
    """
    mode = (paste_hotkey or "dual").strip().lower().replace(" ", "")
    prev_clip = _clipboard_snapshot()
    if not _clipboard_set_text(payload):
        logger.warning(
            "剪贴板写入失败。Linux 可安装: sudo apt install xclip (X11) 或 wl-clipboard (Wayland)"
        )
        return False

    if mode == "dual":
        pasted_ok = _emit_paste_hotkey("ctrl+shift+v")
        fail_label = "ctrl+shift+v（dual）"
    elif mode == "hybrid":
        pasted_ok = _emit_paste_hotkey("shift+insert")
        fail_label = "shift+insert（hybrid）"
    else:
        hk = _normalize_paste_hotkey(paste_hotkey)
        pasted_ok = _emit_paste_hotkey(hk)
        fail_label = hk

    if not pasted_ok:
        logger.warning(
            "粘贴快捷键 %s 模拟失败。Linux 可安装 xdotool（X11）或 wtype（Wayland）。",
            fail_label,
        )
        _restore_clipboard_content(prev_clip)
        return False

    time.sleep(_CLIPBOARD_PASTE_SETTLE_S)
    global _pending_clipboard_restore_timer
    if _pending_clipboard_restore_timer is not None:
        try:
            _pending_clipboard_restore_timer.cancel()
        except Exception:  # noqa: BLE001
            pass
        _pending_clipboard_restore_timer = None

    def _on_done() -> None:
        global _pending_clipboard_restore_timer
        _restore_clipboard_content(prev_clip)
        _pending_clipboard_restore_timer = None

    t = threading.Timer(_CLIPBOARD_RESTORE_DELAY_S, _on_done)
    t.daemon = True
    _pending_clipboard_restore_timer = t
    t.start()
    return True


def type_text(
    text: str,
    append_newline: bool = False,
    method: str = "auto",
    use_clipboard: bool = True,
    pynput_inter_char_delay_s: float = 0.0,
    paste_hotkey: str = "dual",
) -> None:
    global _pynput_inter_char_delay_s
    if not text:
        return

    _pynput_inter_char_delay_s = max(0.0, float(pynput_inter_char_delay_s or 0.0))
    try:
        payload = text + (os.linesep if append_newline else "")
        logger.debug("注入文本(与转写 str 相同): %s", payload)

        method = (method or "auto").lower()

        if method == "paste":
            if _try_clipboard_injection(payload, paste_hotkey=paste_hotkey):
                return
            logger.warning("paste 未完成，尝试 unicode/type 回退: %s", payload)
            if _type_with_unicode_line(payload):
                return
            if _type_with_keyboard(payload):
                return
            logger.error("paste 与键入回退均失败: %s", payload)
            return

        if method == "type":
            order = ["type", "clipboard", "unicode"]
        elif method == "clipboard":
            order = ["clipboard", "type", "unicode"]
        elif method == "unicode":
            order = ["unicode"]
        elif sys.platform == "linux" and method == "auto":
            order = ["unicode", "clipboard", "type"]
        else:
            order = ["type", "clipboard", "unicode"]

        if not use_clipboard:
            order = [m for m in order if m != "clipboard"]
            if not order:
                order = ["unicode", "type"]

        for mode in order:
            if mode == "type" and _type_with_keyboard(payload):
                return
            if mode == "clipboard" and _try_clipboard_injection(payload, paste_hotkey=paste_hotkey):
                return
            if mode == "unicode" and _type_with_unicode_line(payload):
                return

        logger.error("所有文本注入方式均失败: %s", payload)
    finally:
        _pynput_inter_char_delay_s = 0.0
