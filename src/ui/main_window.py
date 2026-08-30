# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================
"""
主窗口：无边框暗色主题。
布局：标题栏 / 状态条 / 35% 字幕显示区 / 控制条 / 历史记录。
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)

from src.ui.theme import ACCENT, BG, BG_2, DIM, FONT_FAMILY, GREEN, RED, TEXT


class MainWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.app = QApplication.instance()

        self._font = controller.config.get("font", 22)
        self._opacity = controller.config.get("alpha", 0.82)
        self._overlay = None          # 由 overlay 模块注入
        self._overlay_visible = False
        self._running = False
        self._hist_count = 0          # 历史句数（QTextBrowser 无自带行数）

        self.setWindowTitle("Ai_EchoSub")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(420, 320)
        self.resize(int(self.screen().availableGeometry().width()
                        * controller.config.get("window_width_ratio", 0.72)), 520)

        self._build_ui()
        self._bind_shortcuts()
        self._connect_controller()

        # 定时轮询识别结果
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(120)

        self._move_to_bottom()
        self._apply_alpha()

    # ------------------------------------------------------------ UI 构建
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QFrame(self, objectName="root")
        frame.setStyleSheet(f"#root{{background:{BG}; border-radius:10px;}}")
        self._frame = frame
        root.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._build_titlebar())
        lay.addWidget(self._build_statusbar())

        subtitle_area, self._ratio = self._build_subtitle_area()
        lay.addWidget(subtitle_area, int(self._ratio * 100))

        lay.addWidget(self._build_controlbar())

        self._history = QTextBrowser(frame)
        self._history.setReadOnly(True)
        self._history.setFrameShape(QFrame.NoFrame)
        self._history.setOpenExternalLinks(False)
        lay.addWidget(self._history, int((1 - self._ratio) * 100))

        self._build_resize_grip(frame)

    def _build_titlebar(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(40)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(4)

        dot = QLabel("●", bar)
        dot.setStyleSheet(f"color:{GREEN}; font-size:14px; background:transparent;")
        title = QLabel("Ai_EchoSub  实时中文字幕", bar)
        title.setStyleSheet(f"color:{TEXT}; font-size:14px; font-weight:bold; background:transparent;")
        lay.addWidget(dot)
        lay.addWidget(title)
        lay.addStretch(1)

        # 作者署名（缩小键左侧）
        author = QLabel("作者：JIE-ONE5926", bar)
        author.setStyleSheet(f"color:{DIM}; font-size:12px; background:transparent;")
        lay.addWidget(author)
        lay.addSpacing(6)

        for text, tip, fn in (
            ("—", "最小化", self.showMinimized),
            ("□", "最大化", self.toggle_max),
            ("✕", "关闭", self.request_quit),
        ):
            b = QLabel(text, bar)
            b.setStyleSheet(
                f"color:{DIM}; font-size:15px; padding:4px 12px; border-radius:6px; background:transparent;")
            b.setToolTip(tip)
            b.mousePressEvent = lambda e, _b=b, _fn=fn: _fn()
            b.enterEvent = lambda e, _b=b: _b.setStyleSheet(
                f"color:{TEXT}; font-size:15px; padding:4px 12px; border-radius:6px; background:{BG_2};")
            b.leaveEvent = lambda e, _b=b: _b.setStyleSheet(
                f"color:{DIM}; font-size:15px; padding:4px 12px; border-radius:6px; background:transparent;")
            lay.addWidget(b)

        # 标题栏拖动
        bar.mousePressEvent = self._titlebar_press
        bar.mouseMoveEvent = self._titlebar_move
        return bar

    def _build_statusbar(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(30)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        self._status = QLabel("就绪", bar)
        self._status.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self._device = QLabel("…", bar)
        self._device.setStyleSheet(f"color:{DIM}; background:transparent;")
        self._level_bar = QProgressBar(bar)
        self._level_bar.setRange(0, 100)
        self._level_bar.setValue(0)
        self._level_bar.setTextVisible(False)
        self._level_bar.setFixedWidth(140)
        self._level_bar.setFixedHeight(6)
        self._level_bar.setStyleSheet(
            f"QProgressBar{{background:{BG_2}; border:none; border-radius:3px;}}"
            f"QProgressBar::chunk{{background:{ACCENT}; border-radius:3px;}}")
        self._count = QLabel("0 句", bar)
        self._count.setStyleSheet(f"color:{DIM}; background:transparent;")

        lay.addWidget(self._status)
        lay.addStretch(1)
        lay.addWidget(self._device)
        lay.addWidget(self._level_bar)
        lay.addWidget(self._count)
        return bar

    def _build_subtitle_area(self) -> tuple[QWidget, float]:
        ratio = self.controller.config.get("subtitle_area_ratio", 0.35)
        ratio = max(0.2, min(0.7, ratio))
        area = QWidget(self)
        area.setStyleSheet("background:transparent;")

        lay = QVBoxLayout(area)
        lay.setContentsMargins(30, 8, 30, 8)

        self._prev_label = QLabel("", area)
        self._prev_label.setStyleSheet(
            f"color:{DIM}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{max(12, self._font - 7)}px;")
        self._prev_label.setWordWrap(True)
        self._prev_label.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)

        self._main_label = QLabel("字幕已就绪，等待语音…", area)
        self._main_label.setStyleSheet(
            f"color:{TEXT}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{self._font}px; font-weight:bold;")
        self._main_label.setWordWrap(True)
        self._main_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        lay.addStretch(1)
        lay.addWidget(self._prev_label)
        lay.addSpacing(6)
        lay.addWidget(self._main_label)
        lay.addStretch(1)
        return area, ratio

    def _build_controlbar(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(10)

        self._btn_toggle = QPushButton("▶  开始字幕", bar)
        self._btn_toggle.setObjectName("primary")
        self._btn_toggle.setMinimumWidth(140)
        self._btn_toggle.clicked.connect(self._on_toggle)

        self._btn_overlay = QPushButton("🖥  悬浮字幕", bar)
        self._btn_overlay.setCheckable(True)
        self._btn_overlay.clicked.connect(self._on_overlay)

        self._btn_history = QPushButton("📋  历史", bar)
        self._btn_history.setCheckable(True)
        self._btn_history.clicked.connect(self._on_history)

        self._btn_settings = QPushButton("⚙  设置", bar)
        self._btn_settings.clicked.connect(self._open_settings)

        lay.addWidget(self._btn_toggle)
        lay.addStretch(1)
        lay.addWidget(self._btn_overlay)
        lay.addWidget(self._btn_history)
        lay.addWidget(self._btn_settings)

        # 历史区默认显示，按钮状态与之一致
        self._btn_history.setChecked(True)
        return bar

    # ---- 右下角缩放把手：窗口可自由缩放，字幕区/历史区等比例缩放 ----
    def _build_resize_grip(self, parent: QWidget):
        grip = QLabel("╲", parent)
        grip.setStyleSheet(f"color:{DIM}; background:transparent; font-size:16px;")
        grip.adjustSize()
        grip.setCursor(Qt.SizeFDiagCursor)
        self._grip = grip
        state = {"on": False, "x": 0, "y": 0, "w": 0, "h": 0}

        def press(e):
            if e.button() == Qt.LeftButton:
                p = e.globalPosition().toPoint()
                state.update(on=True, x=p.x(), y=p.y(), w=self.width(), h=self.height())

        def move(e):
            if state["on"]:
                p = e.globalPosition().toPoint()
                self.resize(max(420, state["w"] + p.x() - state["x"]),
                            max(320, state["h"] + p.y() - state["y"]))

        def release(e):
            state["on"] = False

        grip.mousePressEvent = press
        grip.mouseMoveEvent = move
        grip.mouseReleaseEvent = release
        self._place_grip()

    def _place_grip(self):
        if hasattr(self, "_grip"):
            self._grip.move(self.width() - self._grip.width() - 6,
                            self.height() - self._grip.height() - 6)
            self._grip.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_grip()

    # ------------------------------------------------------------ 行为
    def _on_toggle(self):
        if self._loading():
            return
        self.controller.toggle()

    def _on_overlay(self, checked):
        if self._overlay is None:
            from src.ui.overlay import SubtitleOverlay
            self._overlay = SubtitleOverlay(self.controller)
            self._overlay._closed_cb = self._overlay_closed
            self.controller.caption.connect(self._overlay.show_caption)
            self.controller.preview.connect(self._overlay.show_caption)
        if checked:
            self._overlay.show()
            self._overlay.raise_()
        else:
            self._overlay.hide()
        self._overlay_visible = checked

    def _overlay_closed(self):
        self._overlay_visible = False
        self._btn_overlay.setChecked(False)

    def _on_history(self, checked):
        self._history.setVisible(checked)

    def _open_settings(self):
        from src.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.controller, self)
        if dlg.exec():
            # 字号/透明度即时生效
            self.apply_font(dlg.font_size)
            self._set_opacity(dlg.alpha)
            self.controller.apply_settings()

    def _loading(self) -> bool:
        if self.controller.loading:
            self.controller.status.emit("模型正在加载，请稍候…")
            return True
        return False

    def toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def request_quit(self):
        ret = QMessageBox.question(
            self, "退出", "确定退出 Ai_EchoSub 吗？\n已识别的字幕会自动保存。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            self._really_quit()

    def _really_quit(self):
        self.controller.quit()
        self.app.quit()

    def apply_font(self, size: int):
        self._font = max(12, min(60, size))
        self._main_label.setStyleSheet(
            f"color:{TEXT}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{self._font}px; font-weight:bold;")
        self._prev_label.setStyleSheet(
            f"color:{DIM}; background:transparent; font-family:'{FONT_FAMILY}';"
            f"font-size:{max(12, self._font - 7)}px;")
        self.controller.config.set("font", self._font)

    def _set_opacity(self, v):
        self._opacity = min(0.98, max(0.35, v))
        self.setWindowOpacity(self._opacity)
        self.controller.config.set("alpha", self._opacity)

    def _apply_alpha(self):
        self.setWindowOpacity(self._opacity)

    def _move_to_bottom(self):
        self.adjustSize()
        geo = self.screen().availableGeometry()
        self.move((geo.width() - self.width()) // 2, geo.height() - self.height() - 70)

    # ---- 标题栏拖动 ----
    _drag = None

    def _titlebar_press(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = (e.globalPosition().toPoint() - self.frameGeometry().topLeft())

    def _titlebar_move(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    # ---- 快捷键 ----
    def _bind_shortcuts(self):
        def sc(key, fn):
            s = QShortcut(QKeySequence(key), self)
            s.activated.connect(fn)
            return s

        sc("Esc", self._really_quit)
        sc("+", lambda: self.apply_font(self._font + 2))
        sc("=", lambda: self.apply_font(self._font + 2))
        sc("-", lambda: self.apply_font(self._font - 2))
        sc("Up", lambda: self._set_opacity(self._opacity + 0.08))
        sc("Down", lambda: self._set_opacity(self._opacity - 0.08))
        sc("H", self._on_history_shortcut)

    def _on_history_shortcut(self):
        self._btn_history.setChecked(not self._btn_history.isChecked())
        self._on_history(self._btn_history.isChecked())

    # ---- 控制器信号 ----
    def _connect_controller(self):
        c = self.controller
        c.caption.connect(self.show_caption)
        c.preview.connect(lambda text: self._main_label.setText(text))
        c.history_added.connect(self.add_history)
        c.state_changed.connect(self._on_state)
        c.status.connect(self._status.setText)
        c.device_info.connect(self._device.setText)
        c.audio_level.connect(self._on_level)
        c.device_info.emit(f"{c.device_label} · {c.config.get('model')}")

    def show_caption(self, prev, cur):
        self._prev_label.setText(prev)
        self._main_label.setText(cur or "…")

    def add_history(self, line: str):
        self._hist_count += 1
        self._history.append(line)
        sb = self._history.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._count.setText(f"{self._hist_count} 句")

    def _on_state(self, running: bool):
        self._running = running
        if running:
            self._btn_toggle.setText("⏹  停止")
            self._btn_toggle.setObjectName("danger")
        else:
            self._btn_toggle.setText("▶  开始字幕")
            self._btn_toggle.setObjectName("primary")
        # 刷新样式（setObjectName 后需要 repolish）
        self._btn_toggle.style().unpolish(self._btn_toggle)
        self._btn_toggle.style().polish(self._btn_toggle)

    def _on_level(self, level: float):
        self._level_bar.setValue(min(100, int(level * 260)))

    def _poll(self):
        self.controller.drain()

    def closeEvent(self, e):
        self.controller.quit()
        super().closeEvent(e)
