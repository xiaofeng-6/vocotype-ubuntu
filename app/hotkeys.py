"""Global hotkey management for the application.

Linux 下 `keyboard` 库常要求 root 权限；因此这里提供 pynput 作为 fallback，
以便桌面应用无需 sudo 也能正常启动与使用快捷键（在 X11 下通常可用）。
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)

_MOD_MAP = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "win": "<cmd>",
    "super": "<cmd>",
    "meta": "<cmd>",
    "cmd": "<cmd>",
}


def _to_pynput_combo(combo: str) -> str:
    parts = [p.strip().lower() for p in combo.replace("-", "+").split("+") if p.strip()]
    if not parts:
        return combo
    out: list[str] = []
    for p in parts:
        if p.startswith("<") and p.endswith(">"):
            out.append(p)
            continue
        if p in _MOD_MAP:
            out.append(_MOD_MAP[p])
            continue
        out.append(f"<{p}>")
    return "+".join(out)


@dataclass
class _Reg:
    backend: str
    handle: object


class HotkeyManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._registrations: dict[str, _Reg] = {}
        self._pynput_listener = None
        self._pynput_bindings: dict[str, Callable[[], None]] = {}
        self.enabled = True

    def register(self, combo: str, callback: Callable[[], None]) -> None:
        with self._lock:
            if combo in self._registrations:
                logger.warning("热键 %s 已注册，覆盖旧的回调", combo)
                self._unregister_one(combo)

            # 1) 优先尝试 keyboard（部分 Linux 环境需要 root）
            try:
                import keyboard as _keyboard  # type: ignore

                hotkey_id = _keyboard.add_hotkey(combo, callback)
                self._registrations[combo] = _Reg(backend="keyboard", handle=hotkey_id)
                logger.info("已注册热键 %s (keyboard)", combo)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("keyboard 注册热键失败，将尝试 pynput: %s", exc)

            # 2) fallback：pynput（通常不需要 root；Wayland 可能受限）
            try:
                pcombo = _to_pynput_combo(combo)
                self._pynput_bindings[pcombo] = callback
                self._registrations[combo] = _Reg(backend="pynput", handle=pcombo)
                self._restart_pynput_listener()
                logger.info("已注册热键 %s -> %s (pynput)", combo, pcombo)
                return
            except Exception as exc:  # noqa: BLE001
                self.enabled = False
                logger.error("注册热键 %s 失败（keyboard/pynput 均不可用）: %s", combo, exc)
                raise

    def unregister_all(self) -> None:
        with self._lock:
            for combo in list(self._registrations.keys()):
                self._unregister_one(combo)
            self._registrations.clear()

    def cleanup(self) -> None:
        self.unregister_all()

        try:
            import keyboard as _keyboard  # type: ignore

            _keyboard.unhook_all()
        except Exception:
            pass

        try:
            if self._pynput_listener is not None:
                self._pynput_listener.stop()
                self._pynput_listener = None
                self._pynput_bindings.clear()
        except Exception as exc:
            logger.warning("停止 pynput 监听线程失败: %s", exc)

    def _unregister_one(self, combo: str) -> None:
        reg = self._registrations.get(combo)
        if reg is None:
            return
        if reg.backend == "keyboard":
            try:
                import keyboard as _keyboard  # type: ignore

                _keyboard.remove_hotkey(reg.handle)
            except Exception:
                pass
        elif reg.backend == "pynput":
            try:
                self._pynput_bindings.pop(str(reg.handle), None)
                self._restart_pynput_listener()
            except Exception:
                pass

    def _restart_pynput_listener(self) -> None:
        try:
            from pynput import keyboard as pkeyboard  # type: ignore

            if self._pynput_listener is not None:
                try:
                    self._pynput_listener.stop()
                except Exception:
                    pass
                self._pynput_listener = None

            if not self._pynput_bindings:
                return

            self._pynput_listener = pkeyboard.GlobalHotKeys(dict(self._pynput_bindings))
            self._pynput_listener.start()
        except Exception:
            # 这里不要抛出：否则 GUI 启动会失败
            self.enabled = False


