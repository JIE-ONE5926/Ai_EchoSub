# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
设置内模型下载进度对话框：下载 / 断点续传 / 取消。
"""
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from src.download import download_model
from src.ui.theme import DIM, GREEN, RED, TEXT


class _Bridge(QObject):
    progress = Signal(str, float, float, float)
    finished = Signal(bool, str)


class DownloadDialog(QDialog):
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载模型")
        self.setModal(True)
        self.setFixedSize(480, 200)
        self._cancel_evt = threading.Event()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 18)
        lay.setSpacing(12)

        self._title = QLabel(f"正在下载 {model_name}", self)
        self._title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{TEXT};")
        lay.addWidget(self._title)

        self._status = QLabel("连接下载源…", self)
        self._status.setStyleSheet(f"color:{TEXT};")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._bar = QProgressBar(self)
        self._bar.setRange(0, 1000)
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

    def on_progress(self, status, done_mb, total_mb, speed):
        self._status.setText(status)
        if total_mb > 0:
            self._bar.setValue(int(done_mb / total_mb * 1000))
            self._info.setText(f"{done_mb:.0f} / {total_mb:.0f} MB"
                               + (f" · {speed:.1f} MB/s" if speed > 0 else ""))

    def on_finished(self, ok, message):
        self._done = True
        if ok:
            self._title.setText("下载完成")
            self._title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{GREEN};")
            self._status.setText("模型已就绪，可点击「确定」返回使用。")
            self._cancel.setText("确定")
            self._cancel.setEnabled(True)
        else:
            self._title.setText("下载未完成")
            self._title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{RED};")
            self._status.setText(message)
            self._cancel.setText("关闭")

    def _on_cancel(self):
        if getattr(self, "_done", False):
            self.accept()
            return
        if self._cancel_evt.is_set():
            return
        self._cancel_evt.set()
        self._status.setText("正在取消…")
        self._cancel.setEnabled(False)


def download_with_dialog(base_dir: str, model_name: str, parent=None) -> bool:
    """打开下载进度窗并执行下载。返回是否成功（含用户取消）。"""
    dlg = DownloadDialog(model_name, parent)
    bridge = _Bridge()
    bridge.progress.connect(dlg.on_progress)
    bridge.finished.connect(dlg.on_finished)

    def _work():
        try:
            ok = download_model(
                base_dir, model_name,
                progress_cb=lambda s, d, t, sp: bridge.progress.emit(s, d, t, sp),
                cancel_evt=dlg._cancel_evt)
            bridge.finished.emit(ok, "模型下载未完成（可重试续传）" if not ok else "")
        except Exception as e:
            bridge.finished.emit(False, f"下载失败：{e}")

    threading.Thread(target=_work, daemon=True).start()
    dlg.exec()
    return dlg.result() == 1
