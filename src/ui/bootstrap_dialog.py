# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
首次启动引导对话框：环境检测结果显示 + 模型下载进度 / 模型加载中。
"""
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from src.ui.theme import ACCENT, DIM, GREEN, RED, TEXT


class ProgressBridge(QObject):
    """供后台线程安全地把进度/结果发回主线程（信号自动排队）。"""
    progress = Signal(str, float, float, float)  # status, done_mb, total_mb, speed_mb_s
    finished = Signal(bool, str)                 # ok, message


class BootstrapDialog(QDialog):
    def __init__(self, model_name: str, gpu_ok: bool):
        super().__init__()
        self.setWindowTitle("Ai_EchoSub 首次启动准备")
        self.setModal(True)
        self.setFixedSize(520, 220)
        self._cancel_evt = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(12)

        self._title = QLabel("正在准备运行环境…", self)
        self._title.setStyleSheet(f"font-size:16px; font-weight:bold; color:{TEXT};")
        lay.addWidget(self._title)

        self._env = QLabel(self)
        self._env.setStyleSheet(f"color:{DIM};")
        gpu_txt = f"<span style='color:{GREEN}'>✓ GPU 可用</span>（CUDA 加速）" if gpu_ok \
            else f"<span style='color:{DIM}'>✗ 未检测到 NVIDIA GPU</span>（将使用 CPU）"
        self._env.setText(
            f"环境检测：{gpu_txt}<br>模型：{model_name}（约 1.6GB）")
        lay.addWidget(self._env)

        self._status = QLabel("", self)
        self._status.setStyleSheet(f"color:{TEXT};")
        lay.addWidget(self._status)

        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        lay.addWidget(self._bar)

        bottom = QHBoxLayout()
        self._info = QLabel("", self)
        self._info.setStyleSheet(f"color:{DIM};")
        self._cancel = QPushButton("取消", self)
        self._cancel.clicked.connect(self._on_cancel)
        bottom.addWidget(self._info)
        bottom.addStretch(1)
        bottom.addWidget(self._cancel)
        lay.addLayout(bottom)

    # ---- 阶段切换 ----
    def phase_download(self, cancel_evt=None):
        self._cancel_evt = cancel_evt
        self._title.setText("正在下载识别模型")
        self._status.setText("连接下载源…")
        self._bar.setValue(0)
        self._info.setText("")
        self._cancel.setEnabled(True)
        self._cancel.setText("取消")

    def phase_loading(self):
        self._cancel_evt = None
        self._title.setText("正在加载识别模型")
        self._status.setText("加载中（首次约需十几秒）…")
        self._bar.setRange(0, 0)          # 忙碌样式
        self._bar.setValue(0)
        self._info.setText("")
        self._cancel.setEnabled(False)
        self._cancel.setText("请稍候")

    def phase_error(self, message: str):
        self._title.setText("准备未完成")
        self._status.setText(message)
        self._status.setStyleSheet(f"color:{RED};")
        self._bar.setRange(0, 1)
        self._bar.setValue(0)
        self._cancel.setEnabled(True)
        self._cancel.setText("关闭")

    # ---- 进度 ----
    def on_progress(self, status: str, done_mb: float, total_mb: float, speed: float):
        self._status.setText(status)
        if total_mb > 0:
            self._bar.setRange(0, 1000)
            self._bar.setValue(int(done_mb / total_mb * 1000))
            self._info.setText(f"{done_mb:.0f} / {total_mb:.0f} MB"
                               + (f" · {speed:.1f} MB/s" if speed > 0 else ""))

    def on_finished(self, ok: bool, message: str):
        if ok:
            self.accept()
        else:
            self.phase_error(message)

    def _on_cancel(self):
        if self._cancel_evt is not None:
            self._cancel_evt.set()
            self._status.setText("正在取消…")
            self._cancel.setEnabled(False)
        else:
            self.reject()
