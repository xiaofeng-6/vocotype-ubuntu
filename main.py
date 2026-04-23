"""Command-line entry for the speak-keyboard prototype.

在 Ubuntu / Linux 上：keyboard 与输入注入在部分环境需 sudo 或 uinput
权限；Wayland 下 pynput 可能异常。详见 app.config.DEFAULT_CONFIG 里 output 的注释。
"""

from __future__ import annotations

import os
import sys


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

import argparse
import logging
import threading
import time

import keyboard

from app import HotkeyManager, TranscriptionResult, TranscriptionWorker, load_config, type_text
from app.plugins.dataset_recorder import wrap_result_handler
from app.logging_config import setup_logging


logger = logging.getLogger(__name__)


_TOGGLE_DEBOUNCE_SECONDS = 0.2
_toggle_lock = threading.Lock()
_last_toggle_time = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Speak Keyboard prototype")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single transcription cycle for debugging",
    )
    parser.add_argument("--save-dataset", action="store_true", help="Persist audio/text pairs")
    parser.add_argument("--dataset-dir", default="dataset", help="Dataset output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    
    # 配置日志系统（统一配置）
    from app.config import ensure_logging_dir
    log_dir_abs = ensure_logging_dir(config)
    setup_logging(
        level=config["logging"].get("level", "INFO"),
        log_dir=log_dir_abs
    )

    output_cfg = config.get("output", {})
    output_method = output_cfg.get("method", "auto")
    paste_hotkey = str(output_cfg.get("paste_hotkey", "dual") or "dual")
    append_newline = output_cfg.get("append_newline", False)
    use_clipboard = bool(output_cfg.get("use_clipboard", True))
    try:
        pynput_delay_ms = float(output_cfg.get("pynput_char_delay_ms", 0) or 0)
    except (TypeError, ValueError):
        pynput_delay_ms = 0.0

    # 先创建 worker（无回调）
    try:
        worker = TranscriptionWorker(
            config_path=args.config,
            on_result=None,  # 稍后设置
        )
    except RuntimeError as exc:
        if "FunASR" in str(exc) or "funasr" in str(exc).lower():
            logger.error(
                "若缺少 funasr_onnx，请先安装依赖: python3 -m pip install -r requirements.txt"
            )
        raise
    
    # 创建result handler（需要worker引用）
    worker.on_result = _make_result_handler(
        output_method, append_newline, worker, use_clipboard, pynput_delay_ms, paste_hotkey
    )
    if args.save_dataset:
        worker.on_result = wrap_result_handler(worker.on_result, worker, args.dataset_dir)
    
    hotkeys = HotkeyManager()

    toggle_combo = config["hotkeys"].get("toggle", "f9")
    try:
        hotkeys.register(toggle_combo, lambda: _toggle(worker))
    except ImportError as exc:
        if sys.platform != "win32" and "root" in str(exc).lower():
            logger.error(
                "Linux 上注册全局热键需要 root 或 uinput 权限: %s。"
                "请在项目根目录用当前 venv 解释器: sudo -E .venv/bin/python main.py  （不要 sudo python3，否则会用到系统里没装依赖的 Python）",
                exc,
            )
        raise

    try:
        logger.info("Speak Keyboard 启动完成，按 %s 开始/停止录音，按 Ctrl+C 退出", toggle_combo)
        if sys.platform != "win32":
            # 与 app.config 里 output 注释一致，启动时打一行便于查日志
            logger.info(
                "Linux 提示: 热键/键鼠常需 root 或 uinput; Wayland 下若无法注入可换 X11 或 config output.method"
            )
        if args.once:
            _toggle(worker)
            input("按 Enter 停止并退出...")
            _toggle(worker)
        else:
            keyboard.wait()
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
    finally:
        # 清理所有资源
        try:
            worker.stop()
        except Exception as exc:
            logger.debug("停止 worker 时出错: %s", exc)
        
        try:
            worker.cleanup()
        except Exception as exc:
            logger.debug("清理 worker 时出错: %s", exc)
        
        try:
            hotkeys.cleanup()
        except Exception as exc:
            logger.debug("清理热键时出错: %s", exc)
        
        logger.info("所有资源已清理，正常退出")
        sys.exit(0)


def _make_result_handler(
    output_method: str,
    append_newline: bool,
    worker: TranscriptionWorker,
    use_clipboard: bool,
    pynput_char_delay_ms: float,
    paste_hotkey: str,
):
    def _handle_result(result: TranscriptionResult) -> None:
        if result.error:
            logger.error("转写失败: %s", result.error)
            return

        # 与 funasr_server 里「最终文本」为同一次结果；不再打易误解的 已完成/已提交 比（已修复计数时机）
        stats = worker.transcription_stats
        if worker._transcription_async and stats.get("pending", 0) > 0:
            logger.info(
                "转写成功: %s (推理 %.2fs)  [后台队列还有 %d 段待转写]",
                result.text,
                result.inference_latency,
                stats["pending"],
            )
        else:
            logger.info("转写成功: %s (推理 %.2fs)", result.text, result.inference_latency)
        type_text(
            result.text,
            append_newline=append_newline,
            method=output_method,
            use_clipboard=use_clipboard,
            pynput_inter_char_delay_s=pynput_char_delay_ms / 1000.0,
            paste_hotkey=paste_hotkey,
        )

    return _handle_result


def _toggle(worker: TranscriptionWorker) -> None:
    global _last_toggle_time
    now = time.monotonic()
    with _toggle_lock:
        if now - _last_toggle_time < _TOGGLE_DEBOUNCE_SECONDS:
            logger.debug("忽略快速重复的录音切换请求 (%.3fs)", now - _last_toggle_time)
            return
        _last_toggle_time = now

    if worker.is_running:
        # 停止录音，提交转录任务
        worker.stop()
        stats = worker.transcription_stats
        if stats["pending"] > 0:
            logger.info(
                "录音已停止并提交转录，队列中还有 %d 个任务等待处理",
                stats["pending"]
            )
    else:
        # 开始录音
        stats = worker.transcription_stats
        if stats["pending"] > 0:
            logger.info(
                "开始录音（后台还有 %d 个转录任务正在处理）",
                stats["pending"]
            )
        worker.start()


if __name__ == "__main__":
    main()

