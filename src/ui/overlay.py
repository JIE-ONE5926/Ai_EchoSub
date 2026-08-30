# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
悬浮字幕小窗：无边框、置顶、半透明，可拖动/右下角缩放/右键菜单。
显示上一句 + 当前句，关闭后字幕回到主窗口。
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget,
)

from src.ui.theme import BG, BG_2, DIM, FONT_FAMILY, TEXT


class SubtitleOverlay(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._font = controller.config.get("font", 22)
        self._opacity = controller.config.get("alpha", 0.82)

        self.setWindowTitle("Ai_EchoSub 悬浮字幕")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 与主程序一致的图标（任务栏/Alt-Tab）
        try:
            from PySide6.QtWidgets import QApplication
            self.setWindowIcon(QApplication.instance().windowIcon())
        except Exception:
            pass
        self.setMinimumSize(240, 70)
        sw = self.screen().availableGeometry().width()
        self.resize(int(sw * controller.config.get("overlay_ratio", 0.72)), 150)
        self.setWindowOpacity(self._opacity)

        self._build_ui()
        self._build_menu()

        # 拖动/缩放状态
        self._drag = None
        self._resize = None

        # 每 2 秒重新置顶
        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self._keep_top)
        self._top_timer.start(2000)

        self._move_to_bottom()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        frame = QFrame(self, objectName="overlay")
        frame.setStyleSheet(f"#overlay{{background:{BG}; border:1px solid {BG_2}; border-radius:10px;}}")
        root.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(24, 10, 24, 10)

        self._prev = QLabel("", frame)
        self._prev.setStyleSheet(
            f"color:{DIM}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{max(12, self._font - 7)}px;")
        self._prev.setWordWrap(True)
        self._prev.setAlignment(Qt.AlignHCenter)

        self._main = QLabel("…", frame)
        self._main.setStyleSheet(
            f"color:{TEXT}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{self._font}px; font-weight:bold;")
        self._main.setWordWrap(True)
        self._main.setAlignment(Qt.AlignHCenter)

        lay.addStretch(1)
        lay.addWidget(self._prev)
        lay.addSpacing(4)
        lay.addWidget(self._main)
        lay.addStretch(1)

        # 右下角缩放把手
        self._grip = QLabel("╲", frame)
        self._grip.setStyleSheet(f"color:{DIM}; background:transparent; font-size:14px;")
        self._grip.adjustSize()
        self._grip.move(frame.width() - self._grip.width() - 8,
                        frame.height() - self._grip.height() - 8)

        # 整个窗口可拖动 + 右键菜单
        for w in (frame, self._prev, self._main):
            w.mousePressEvent = self._on_press
            w.mouseMoveEvent = self._on_move
            w.mouseReleaseEvent = self._on_release
            w.setContextMenuPolicy(Qt.CustomContextMenu)
            w.customContextMenuRequested.connect(self._popup)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_grip"):
            self._grip.move(self.width() - self._grip.width() - 10,
                            self.height() - self._grip.height() - 10)

    def _build_menu(self):
        self._menu = QMenu(self)
        self._menu.addAction("字号增大 (+)", lambda: self._change_font(2))
        self._menu.addAction("字号减小 (-)", lambda: self._change_font(-2))
        self._menu.addSeparator()
        self._menu.addAction("更不透明 (↑)", lambda: self._set_opacity(self._opacity + 0.08))
        self._menu.addAction("更透明 (↓)", lambda: self._set_opacity(self._opacity - 0.08))
        self._menu.addSeparator()
        self._menu.addAction("移到屏幕底部", lambda: self._move_to("bottom"))
        self._menu.addAction("移到屏幕顶部", lambda: self._move_to("top"))
        self._menu.addAction("移到屏幕中间", lambda: self._move_to("middle"))
        self._menu.addSeparator()
        self._menu.addAction("回到主窗口", self._close_to_main)

    def _popup(self, pos):
        self._menu.exec(self.mapToGlobal(pos))

    def show_caption(self, prev, cur):
        self._prev.setText(prev)
        self._main.setText(cur or "…")

    def _close_to_main(self):
        self.hide()
        if getattr(self, "_closed_cb", None):
            self._closed_cb()

    def _change_font(self, d):
        self._font = max(12, min(60, self._font + d))
        self._main.setStyleSheet(
            f"color:{TEXT}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{self._font}px; font-weight:bold;")
        self._prev.setStyleSheet(
            f"color:{DIM}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{max(12, self._font - 7)}px;")
        self.controller.config.set("font", self._font)

    def _set_opacity(self, v):
        self._opacity = min(0.98, max(0.35, v))
        self.setWindowOpacity(self._opacity)
        self.controller.config.set("alpha", self._opacity)

    # ---- 拖动 / 缩放 ----
    def _on_press(self, e):
        if e.button() == Qt.LeftButton:
            if self._in_grip(e.position()):
                self._resize = (e.globalPosition().toPoint(), self.size())
            else:
                self._drag = (e.globalPosition().toPoint() - self.frameGeometry().topLeft())

    def _on_move(self, e):
        if self._resize is not None:
            origin, size = self._resize
            delta = e.globalPosition().toPoint() - origin
            self.resize(max(240, size.width() + delta.x()),
                        max(70, size.height() + delta.y()))
        elif self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def _on_release(self, e):
        self._drag = None
        self._resize = None

    def _in_grip(self, pos) -> bool:
        r = self._grip.geometry()
        return r.adjusted(-12, -12, 4, 4).contains(int(pos.x()), int(pos.y()))

    def _keep_top(self):
        self.raise_()

    def _move_to(self, pos):
        geo = self.screen().availableGeometry()
        w, h = self.width(), self.height()
        x = (geo.width() - w) // 2
        y = {"bottom": geo.height() - h - 60, "top": 20, "middle": (geo.height() - h) // 2}[pos]
        self.move(x, y)

    def _move_to_bottom(self):
        self._move_to("bottom")
