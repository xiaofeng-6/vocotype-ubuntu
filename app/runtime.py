"""应用运行时：配置、转写 Worker、热键与生命周期（CLI / GUI 共用）。"""

from __future__ import annotations

import logging
import sys
import threading
import time
from argparse import Namespace
from dataclasses import dataclass

from app import HotkeyManager, TranscriptionResult, TranscriptionWorker, load_config, type_text
from app.config import ensure_logging_dir
from app.logging_config import setup_logging
from app.plugins.dataset_recorder import wrap_result_handler

logger = logging.getLogger(__name__)

_TOGGLE_DEBOUNCE_SECONDS = 0.2
_toggle_lock = threading.Lock()
_last_toggle_time = 0.0


@dataclass
class Runtime:
    args: Namespace
    config: dict
    worker: TranscriptionWorker
    hotkeys: HotkeyManager
    toggle_combo: str
    output_method: str
    append_newline: bool
    use_clipboard: bool
    pynput_delay_ms: float
    paste_hotkey: str


def make_result_handler(
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


def toggle_recording(worker: TranscriptionWorker) -> None:
    global _last_toggle_time
    now = time.monotonic()
    with _toggle_lock:
        if now - _last_toggle_time < _TOGGLE_DEBOUNCE_SECONDS:
            logger.debug("忽略快速重复的录音切换请求 (%.3fs)", now - _last_toggle_time)
            return
        _last_toggle_time = now

    if worker.is_running:
        worker.stop()
        stats = worker.transcription_stats
        if stats["pending"] > 0:
            logger.info(
                "录音已停止并提交转录，队列中还有 %d 个任务等待处理",
                stats["pending"],
            )
    else:
        stats = worker.transcription_stats
        if stats["pending"] > 0:
            logger.info(
                "开始录音（后台还有 %d 个转录任务正在处理）",
                stats["pending"],
            )
        worker.start()


def init_runtime(args: Namespace) -> Runtime:
    config = load_config(args.config)
    log_dir_abs = ensure_logging_dir(config)
    setup_logging(
        level=config["logging"].get("level", "INFO"),
        log_dir=log_dir_abs,
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

    try:
        worker = TranscriptionWorker(
            config_path=args.config,
            on_result=None,
        )
    except RuntimeError as exc:
        if "FunASR" in str(exc) or "funasr" in str(exc).lower():
            logger.error(
                "若缺少 funasr_onnx，请先安装依赖: python3 -m pip install -r requirements.txt"
            )
        raise

    worker.on_result = make_result_handler(
        output_method, append_newline, worker, use_clipboard, pynput_delay_ms, paste_hotkey
    )
    if args.save_dataset:
        worker.on_result = wrap_result_handler(worker.on_result, worker, args.dataset_dir)

    hotkeys = HotkeyManager()
    toggle_combo = config["hotkeys"].get("toggle", "f9")

    return Runtime(
        args=args,
        config=config,
        worker=worker,
        hotkeys=hotkeys,
        toggle_combo=toggle_combo,
        output_method=output_method,
        append_newline=append_newline,
        use_clipboard=use_clipboard,
        pynput_delay_ms=pynput_delay_ms,
        paste_hotkey=paste_hotkey,
    )


def register_toggle_hotkey(rt: Runtime) -> None:
    try:
        rt.hotkeys.register(rt.toggle_combo, lambda: toggle_recording(rt.worker))
    except Exception as exc:  # noqa: BLE001
        # 桌面应用必须能在无 root 权限下启动；热键失败则降级为仅按钮可用
        logger.error("全局热键注册失败（将仅保留窗口按钮可用）: %s", exc)
        rt.hotkeys.enabled = False


def shutdown_runtime(rt: Runtime) -> None:
    try:
        rt.worker.stop()
    except Exception as exc:
        logger.debug("停止 worker 时出错: %s", exc)

    try:
        rt.worker.cleanup()
    except Exception as exc:
        logger.debug("清理 worker 时出错: %s", exc)

    try:
        rt.hotkeys.cleanup()
    except Exception as exc:
        logger.debug("清理热键时出错: %s", exc)

    logger.info("所有资源已清理，正常退出")
