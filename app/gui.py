"""VocoType 桌面图形界面（CustomTkinter 实现）。"""

from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

import customtkinter as ctk

from app.runtime import Runtime, toggle_recording

logger = logging.getLogger(__name__)


def run_gui(rt: Runtime) -> None:
    """在已有 Runtime（含热键与 worker）上启动主窗口，阻塞至窗口关闭。"""
    app = VocotypeCtkApp(rt)
    app.mainloop()


class VocotypeCtkApp(ctk.CTk):
    def __init__(self, rt: Runtime) -> None:
        super().__init__()
        self._rt = rt
        self._poll_interval_ms = 120
        self._is_recording = False

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("VocoType 语音输入")
        self.geometry("560x420")
        self.minsize(460, 340)
        self.configure(fg_color="#f4f6fb")
        self._font_family = self._pick_font_family()

        self._status_var = tk.StringVar(value="就绪")
        self._hint_var = tk.StringVar(value="点击开始录音")
        self._record_circle_fill = "#7f92cb"

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(self._poll_interval_ms, self._refresh_recording_state)

    def _build_ui(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        status_card = ctk.CTkFrame(main, corner_radius=16, fg_color="#ffffff")
        status_card.pack(fill=tk.X)

        self._status_dot = ctk.CTkLabel(
            status_card,
            text="",
            width=10,
            height=10,
            fg_color="#8fa2d7",
            corner_radius=5,
        )
        self._status_dot.pack(side=tk.LEFT, padx=(14, 10), pady=14)

        ctk.CTkLabel(
            status_card,
            text="状态",
            text_color="#4c5d7f",
            font=self._font(14, "bold"),
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            status_card,
            textvariable=self._status_var,
            text_color="#22314f",
            font=self._font(16, "bold"),
        ).pack(side=tk.LEFT, padx=(10, 0))

        body_card = ctk.CTkFrame(main, corner_radius=20, fg_color="#ffffff")
        body_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        ctk.CTkLabel(
            body_card,
            text="VocoType 语音输入",
            text_color="#1d2b45",
            font=self._font(24, "bold"),
        ).pack(pady=(18, 6))

        hotkey = str(self._rt.config.get("hotkeys", {}).get("toggle", "f9")).upper()
        ctk.CTkLabel(
            body_card,
            text=f"全局快捷键：{hotkey}（与下方按钮一致）",
            text_color="#6d7da0",
            font=self._font(13),
        ).pack()

        self._record_button = tk.Canvas(
            body_card,
            width=172,
            height=172,
            highlightthickness=0,
            bd=0,
            bg="#ffffff",
            cursor="hand2",
        )
        self._record_button_circle = self._record_button.create_oval(
            0,
            0,
            172,
            172,
            fill=self._record_circle_fill,
            outline=self._record_circle_fill,
        )
        self._record_button.bind("<Button-1>", lambda _event: self._on_toggle_click())
        self._record_button.pack(pady=(18, 8))

        ctk.CTkLabel(
            body_card,
            textvariable=self._hint_var,
            text_color="#5f708f",
            font=self._font(14),
        ).pack()

        bottom = ctk.CTkFrame(body_card, fg_color="transparent")
        bottom.pack(fill=tk.X, padx=14, pady=(18, 12))
        ctk.CTkButton(
            bottom,
            text="退出",
            width=88,
            fg_color="#ebeff8",
            hover_color="#dbe4f4",
            text_color="#2c3c58",
            command=self._on_close,
        ).pack(side=tk.RIGHT)

    def _on_toggle_click(self) -> None:
        try:
            toggle_recording(self._rt.worker)
        except Exception as exc:  # noqa: BLE001
            logger.exception("切换录音失败")
            messagebox.showerror("错误", str(exc), parent=self)

    def _refresh_recording_state(self) -> None:
        try:
            is_recording = bool(self._rt.worker.is_running)
            if is_recording:
                self._status_var.set("正在录音…")
                self._hint_var.set("点击停止录音")
            else:
                pending = self._rt.worker.transcription_stats.get("pending", 0)
                if pending and pending > 0:
                    self._status_var.set(f"转写队列中（待处理 {pending} 段）")
                else:
                    self._status_var.set("就绪")
                self._hint_var.set("点击开始录音")

            if is_recording != self._is_recording:
                self._is_recording = is_recording
                if is_recording:
                    self._record_circle_fill = "#dd5a6f"
                    self._record_button.itemconfigure(
                        self._record_button_circle,
                        fill=self._record_circle_fill,
                        outline=self._record_circle_fill,
                    )
                    self._status_dot.configure(fg_color="#dd5a6f")
                else:
                    self._record_circle_fill = "#7f92cb"
                    self._record_button.itemconfigure(
                        self._record_button_circle,
                        fill=self._record_circle_fill,
                        outline=self._record_circle_fill,
                    )
                    self._status_dot.configure(fg_color="#8fa2d7")
        except tk.TclError:
            return
        self.after(self._poll_interval_ms, self._refresh_recording_state)

    def _font(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=self._font_family, size=size, weight=weight)

    def _pick_font_family(self) -> str:
        preferred = [
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans SC",
            "Microsoft YaHei",
            "PingFang SC",
            "WenQuanYi Micro Hei",
            "Noto Sans",
            "DejaVu Sans",
            "Ubuntu",
            "Cantarell",
        ]
        bitmap_like = {
            "Fixed",
            "Terminal",
            "System",
            "TkFixedFont",
        }
        try:
            installed = set(tkfont.families(self))
            default_font = tkfont.nametofont("TkDefaultFont")
            family = default_font.actual("family")
        except tk.TclError:
            return "TkDefaultFont"
        for name in preferred:
            if name in installed:
                return name
        if family and family not in bitmap_like:
            return family
        return "DejaVu Sans"

    def _on_close(self) -> None:
        if self._rt.worker.is_running:
            if not messagebox.askyesno(
                "确认",
                "当前仍在录音，确定要退出吗？",
                parent=self,
            ):
                return
        self.quit()
        self.destroy()
