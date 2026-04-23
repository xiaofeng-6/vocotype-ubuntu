"""Audio capture utilities built on sounddevice."""

from __future__ import annotations

import logging
import queue
import threading
import os
from typing import List, Optional, Union

import numpy as np
import sounddevice as sd


logger = logging.getLogger(__name__)


class AudioCaptureError(RuntimeError):
    """Raised when the audio capture stream cannot be started."""


class AudioCapture:
    """Capture audio frames from the default (or configured) microphone.

    输出到队列的音频恒为 ``target_sample_rate``（默认 16kHz，与 ASR 一致）。
    若声卡不支持该速率，会在本机支持的速率下打开流，并在回调中重采样到目标速率。
    """

    def __init__(
        self,
        sample_rate: int,
        block_ms: int,
        device: Optional[Union[int, str]] = None,
        queue_size: int = 200,
    ) -> None:
        # 识别链路的标称采样率（写入 wav、送 ASR）
        self.target_sample_rate = sample_rate
        self.sample_rate = sample_rate  # 与历史代码一致，表示「输出」速率
        self.block_ms = block_ms
        self.device = device
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=queue_size)
        self._stream: Optional[sd.RawInputStream] = None
        self._lock = threading.Lock()
        self._running = False
        # 当前 PortAudio 流实际使用的采样率（打开流后赋值）
        self._stream_sample_rate = sample_rate
        self._block_size = max(1, int(self._stream_sample_rate * self.block_ms / 1000))

    @property
    def queue(self) -> "queue.Queue[np.ndarray]":
        return self._queue

    def _input_devices_to_try(self) -> List[object]:
        """要尝试的输入设备列表。

        ``sudo`` 下 PortAudio 的默认输入常为 ``-1``，不能用 ``device=None`` 盲开；
        需列出所有带输入通道的设备下标依次尝试。用户若在 config 里指定 ``audio.device`` 则只试该项。
        """
        if self.device is not None:
            return [self.device]

        ordered: List[int] = []
        seen: set[int] = set()
        try:
            default_in, _ = sd.default.device
            if default_in is not None and int(default_in) >= 0:
                ordered.append(int(default_in))
                seen.add(int(default_in))
        except Exception as exc:
            logger.debug("读取默认输入设备: %s", exc)
        try:
            for i, info in enumerate(sd.query_devices()):
                if info.get("max_input_channels", 0) <= 0:
                    continue
                if i not in seen:
                    seen.add(i)
                    ordered.append(i)
        except Exception as exc:
            logger.error("枚举 PortAudio 设备失败: %s", exc)
        if not ordered and os.geteuid() == 0:
            logger.error(
                "以 root 运行但未发现任何输入设备。常见原因：PulseAudio/PipeWire 只挂在用户会话上。"
                "可尝试: sudo -E 且保留 XDG_RUNTIME_DIR，或在 config.json 中设置 audio.device 为具体设备编号；"
                "用同一用户执行: python -c \"import sounddevice as sd; print(sd.query_devices())\" 查看编号。"
            )
        return ordered

    def _candidate_sample_rates(self, device: object) -> List[int]:
        """按顺序尝试的输入采样率：先目标值，再设备默认，再常见值。"""
        out: List[int] = []
        seen: set[int] = set()

        def add(rate: int) -> None:
            if rate > 0 and rate not in seen:
                seen.add(rate)
                out.append(rate)

        add(self.target_sample_rate)
        try:
            if device is not None and not (isinstance(device, int) and device < 0):
                info = sd.query_devices(device, "input")
                ds = info.get("default_samplerate")
                if ds:
                    add(int(ds))
        except Exception as exc:
            logger.debug("查询设备 %s 默认采样率: %s", device, exc)
        for r in (48000, 44100, 32000, 22050, 8000):
            add(r)
        return out

    def start(self) -> None:
        with self._lock:
            if self._running:
                return

            self.flush()
            devices_to_try = self._input_devices_to_try()
            if not devices_to_try:
                msg = "未找到任何音频输入设备，无法录音（请检查麦克风与权限）。"
                logger.error(msg)
                raise AudioCaptureError(msg)

            last_exc: Optional[Exception] = None
            for dev in devices_to_try:
                for sr in self._candidate_sample_rates(dev):
                    self._stream_sample_rate = sr
                    self._block_size = max(1, int(sr * self.block_ms / 1000))
                    try:
                        stream = self._create_stream(dev)
                        stream.start()
                        self._stream = stream
                        self._running = True
                        if sr != self.target_sample_rate:
                            logger.info(
                                "音频采集已启动，设备采样率=%sHz，已重采样至 %sHz；块=%s 样本，device=%s",
                                sr,
                                self.target_sample_rate,
                                self._block_size,
                                dev,
                            )
                        else:
                            logger.info(
                                "音频采集已启动，采样率=%sHz，块=%s 样本，device=%s",
                                sr,
                                self._block_size,
                                dev,
                            )
                        return
                    except Exception as exc:
                        last_exc = exc
                        logger.warning(
                            "打开输入流失败 device=%s sample_rate=%s: %s",
                            dev,
                            sr,
                            exc,
                        )

            msg = f"无法创建音频输入流（已尝试多种采样率与设备）: {last_exc}"
            logger.error(msg)
            raise AudioCaptureError(msg) from last_exc

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return

            assert self._stream is not None
            self._stream.stop()
            self._stream.close()
            self._stream = None
            self._running = False
            logger.info("音频采集已停止")

    def flush(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _create_stream(self, device: object) -> sd.RawInputStream:
        try:
            return sd.RawInputStream(
                samplerate=self._stream_sample_rate,
                blocksize=self._block_size,
                dtype="int16",
                channels=1,
                callback=self._callback,
                device=device,
            )
        except Exception as exc:
            msg = f"无法创建音频输入流: {exc}"
            logger.error(msg)
            raise AudioCaptureError(msg) from exc

    def _callback(self, in_data, frames, time, status):  # type: ignore[override]
        if status:
            logger.warning("音频流状态: %s", status)

        frame = np.frombuffer(in_data, dtype=np.int16)
        if self._stream_sample_rate != self.target_sample_rate:
            import librosa

            y = frame.astype(np.float32) / 32768.0
            y_out = librosa.resample(
                y,
                orig_sr=self._stream_sample_rate,
                target_sr=self.target_sample_rate,
                res_type="kaiser_fast",
            )
            frame = np.clip(y_out * 32768.0, -32768, 32767).astype(np.int16)

        try:
            self._queue.put_nowait(frame.copy())
        except queue.Full:
            logger.warning("音频队列已满，丢弃音频帧")
