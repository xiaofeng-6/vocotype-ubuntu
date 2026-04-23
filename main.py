"""Command-line entry for the speak-keyboard prototype.

在 Ubuntu / Linux 上：keyboard 与输入注入在部分环境需 sudo 或 uinput
权限；Wayland 下 pynput 可能异常。详见 app.config.DEFAULT_CONFIG 里 output 的注释。

默认启动图形窗口；需要纯终端时可加 --cli。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time


def _fix_audio_env_for_sudo() -> None:
    """sudo 时把 XDG_RUNTIME_DIR 指回真实用户，便于连接 PipeWire/Pulse 枚举麦克风。

    否则 root 看到的「用户会话」里没有 /run/user/<uid>/ 下的音频套接字，PortAudio 列不出任何输入设备。
    必须在 import app（进而 import sounddevice）之前调用。
    """
    if os.name != "posix":
        return
    try:
        if os.geteuid() != 0:
            return
    except AttributeError:
        return
    suid = os.environ.get("SUDO_UID")
    if not suid:
        return
    run_dir = f"/run/user/{suid}"
    if os.path.isdir(run_dir):
        os.environ["XDG_RUNTIME_DIR"] = run_dir
    pulse_native = os.path.join(run_dir, "pulse", "native")
    if os.path.exists(pulse_native):
        os.environ.setdefault("PULSE_SERVER", f"unix:{pulse_native}")


_fix_audio_env_for_sudo()

from app.gui import run_gui  # noqa: E402
from app.runtime import (  # noqa: E402
    init_runtime,
    register_toggle_hotkey,
    shutdown_runtime,
    toggle_recording,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Speak Keyboard prototype")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="仅命令行界面（无窗口，日志在终端）",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single transcription cycle for debugging",
    )
    parser.add_argument("--save-dataset", action="store_true", help="Persist audio/text pairs")
    parser.add_argument("--dataset-dir", default="dataset", help="Dataset output directory")
    return parser.parse_args()


def _force_cli_if_no_display(args: argparse.Namespace) -> None:
    if args.cli or sys.platform == "win32":
        return
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    logger.warning("未检测到 DISPLAY / WAYLAND_DISPLAY，自动使用 --cli")
    args.cli = True


def main() -> None:
    args = parse_args()
    _force_cli_if_no_display(args)

    rt = init_runtime(args)
    register_toggle_hotkey(rt)

    try:
        if not args.cli:
            logger.info(
                "Speak Keyboard 图形界面已打开，按 %s 或使用窗口按钮开始/停止录音",
                rt.toggle_combo,
            )
        else:
            logger.info(
                "Speak Keyboard 启动完成，按 %s 开始/停止录音，按 Ctrl+C 退出",
                rt.toggle_combo,
            )
        if sys.platform != "win32":
            logger.info(
                "Linux 提示: 热键/键鼠常需 root 或 uinput; Wayland 下若无法注入可换 X11 或 config output.method"
            )

        if args.once:
            toggle_recording(rt.worker)
            input("按 Enter 停止并退出...")
            toggle_recording(rt.worker)
        elif args.cli:
            if not rt.hotkeys.enabled:
                logger.error("热键不可用，无法在 --cli 模式下操作；请移除 --cli 或改用窗口按钮。")
                return
            while True:
                time.sleep(3600)
        else:
            run_gui(rt)
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
    finally:
        shutdown_runtime(rt)
        sys.exit(0)


if __name__ == "__main__":
    main()
