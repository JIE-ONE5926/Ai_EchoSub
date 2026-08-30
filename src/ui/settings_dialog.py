# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
设置对话框（单页深色表单）：
  识别模型 / 推荐下载 / 监听设备 / 计算设备 / 断句 / 合并 / 流式 / 字号 / 透明度 / 领域提示词
  底部：恢复默认 · 取消 · 确定
"""
import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from src import prompt_config
from src.config import DEFAULT_CONFIG, MODEL_SOURCES
from src.download import model_ready, models_dir
from src.engine.recorder import get_output_devices
from src.ui.download_dialog import download_with_dialog
from src.ui.theme import DIM


class SettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cfg = controller.config
        self.base_dir = controller.base_dir
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumSize(500, 560)

        self.font_size = self.cfg.get("font", 22)
        self.alpha = self.cfg.get("alpha", 0.82)

        # 滚动容器（单页表单，字段多时可滚动）
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        self.form = QFormLayout(content)
        self.form.setHorizontalSpacing(16)
        self.form.setVerticalSpacing(10)
        self._build_form(content)
        scroll.setWidget(content)

        # 底部按钮
        bottom = QHBoxLayout()
        self._reset_btn = QPushButton("恢复默认")
        self._reset_btn.clicked.connect(self._restore_defaults)
        self._ok_btn = QPushButton("确定")
        self._ok_btn.setObjectName("primary")
        self._ok_btn.clicked.connect(self._apply)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(self._reset_btn)
        bottom.addStretch(1)
        bottom.addWidget(self._cancel_btn)
        bottom.addWidget(self._ok_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(scroll, 1)
        lay.addLayout(bottom)

    # ------------------------------------------------------------ 表单构建
    def _build_form(self, content: QWidget):
        f = self.form

        # ---- 识别模型 ----
        m_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self._populate_model_combo()
        self.model_folder_btn = QPushButton("📁 模型文件夹")
        self.model_folder_btn.clicked.connect(self._open_models_folder)
        m_row.addWidget(self.model_combo, 1)
        m_row.addWidget(self.model_folder_btn)
        f.addRow("识别模型", m_row)

        # ---- 模型下载（下拉选择，紧凑不占地方）----
        d_row = QHBoxLayout()
        self.dl_combo = QComboBox()
        self.dl_btn = QPushButton("⬇ 下载")
        self.dl_btn.clicked.connect(self._download_selected)
        self.dl_manual_btn = QPushButton("❓ 手动说明")
        self.dl_manual_btn.setStyleSheet(f"color:{DIM}; font-size:12px;")
        self.dl_manual_btn.clicked.connect(self._show_manual)
        d_row.addWidget(self.dl_combo, 1)
        d_row.addWidget(self.dl_btn)
        d_row.addWidget(self.dl_manual_btn)
        f.addRow("模型下载", d_row)
        self._refresh_dl_combo()

        # ---- 监听设备 ----
        self.device_combo = QComboBox()
        self._populate_devices()
        f.addRow("监听设备", self.device_combo)
        self._dev_hint = QLabel("选择要监听的输出设备；默认跟随系统当前输出。", content)
        self._dev_hint.setStyleSheet(f"color:{DIM}; font-size:11px;")
        f.addRow("", self._dev_hint)

        # ---- 计算设备 ----
        self.compute = QComboBox()
        self.compute.addItems(["auto", "cuda", "cpu"])
        self.compute.setCurrentText(self.cfg.get("device", "auto"))
        f.addRow("计算设备", self.compute)
        self._compute_hint = QLabel("auto：有 NVIDIA 显卡自动用 GPU，否则 CPU。", content)
        self._compute_hint.setStyleSheet(f"color:{DIM}; font-size:11px;")
        f.addRow("", self._compute_hint)

        # ---- 断句 / beam / 合并 / 流式 ----
        self.silence = QSpinBox()
        self.silence.setRange(200, 1500)
        self.silence.setSuffix(" ms")
        self.silence.setValue(self.cfg.get("silence_ms", 400))
        f.addRow("停顿断句阈值", self.silence)

        self.beam = QSpinBox()
        self.beam.setRange(1, 5)
        self.beam.setValue(self.cfg.get("beam", 5))
        f.addRow("beam 搜索宽度", self.beam)

        self.merge = QCheckBox("把碎片字幕拼成完整句")
        self.merge.setChecked(self.cfg.get("merge", True))
        f.addRow("句子平滑合并", self.merge)

        self.stream = QSpinBox()
        self.stream.setRange(0, 3000)
        self.stream.setSuffix(" ms")
        self.stream.setSpecialValueText("关闭")
        self.stream.setValue(self.cfg.get("stream_ms", 0))
        f.addRow("边说边出字", self.stream)

        # ---- 字号 / 透明度 ----
        self.font = QSpinBox()
        self.font.setRange(12, 60)
        self.font.setValue(self.font_size)
        f.addRow("字幕字号", self.font)

        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.35, 0.98)
        self.opacity.setSingleStep(0.05)
        self.opacity.setDecimals(2)
        self.opacity.setValue(self.alpha)
        f.addRow("不透明度", self.opacity)

        # ---- 领域提示词 ----
        p_row = QHBoxLayout()
        self.prompt_combo = QComboBox()
        self._populate_prompt_combo()
        self.prompt_folder_btn = QPushButton("📁 打开提示词文件夹")
        self.prompt_folder_btn.clicked.connect(self._open_prompt_folder)
        p_row.addWidget(self.prompt_combo, 1)
        p_row.addWidget(self.prompt_folder_btn)
        f.addRow("领域提示词", p_row)
        self._prompt_hint = QLabel(
            "下拉直接选择生效模板；打开文件夹后，右键 提示词_config.json → "
            "打开方式 → 记事本（文本文档），修改保存后点「确定」生效。", content)
        self._prompt_hint.setStyleSheet(f"color:{DIM}; font-size:11px;")
        self._prompt_hint.setWordWrap(True)
        f.addRow("", self._prompt_hint)

    # ------------------------------------------------------------ 填充
    def _populate_devices(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        try:
            default_name, devices = get_output_devices()
        except Exception as e:
            default_name, devices = "", []
            print(f"[设置] 枚举输出设备失败：{e}", flush=True)
        self.device_combo.addItem(f"默认（当前监听：{default_name or '未知'}）", None)
        for idx, name, rate in devices:
            self.device_combo.addItem(f"{name} ({rate}Hz)", idx)
        saved = self.cfg.get("device_index")
        if saved is not None:
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == saved:
                    self.device_combo.setCurrentIndex(i)
                    break
        self.device_combo.blockSignals(False)

    def _populate_prompt_combo(self):
        self.prompt_combo.clear()
        names = prompt_config.list_templates(self.base_dir)
        self.prompt_combo.addItems(names)
        active = prompt_config.load(self.base_dir).get("active", "")
        if active in names:
            self.prompt_combo.setCurrentText(active)

    def _populate_model_combo(self):
        self.model_combo.clear()
        for m in self._available_models():
            self.model_combo.addItem(m)
        cur = self.cfg.get("model")
        if self.model_combo.findText(cur) >= 0:
            self.model_combo.setCurrentText(cur)

    def _available_models(self):
        root = models_dir(self.base_dir)
        found = []
        if os.path.isdir(root):
            for d in sorted(os.listdir(root)):
                if os.path.isfile(os.path.join(root, d, "model.bin")):
                    found.append(d)
        return found or [self.cfg.get("model")]

    def _refresh_dl_combo(self):
        """模型下载下拉：列出尚未下载的模型（含体积），供不同配置用户选择。"""
        self.dl_combo.clear()
        root = models_dir(self.base_dir)
        missing = [(n, s) for n, s in MODEL_SOURCES.items() if not model_ready(root, n)]
        if not missing:
            self.dl_combo.addItem("所有模型均已下载 ✓")
            self.dl_btn.setEnabled(False)
            return
        self.dl_btn.setEnabled(True)
        for name, src in missing:
            gb = src['model_bin_mb'] / 1000
            self.dl_combo.addItem(f"{name}  (约 {gb:.2f} GB)", name)

    def _download_selected(self):
        name = self.dl_combo.currentData()
        if not name:
            return
        if download_with_dialog(self.base_dir, name, self):
            self._populate_model_combo()
            self._refresh_dl_combo()

    def _show_manual(self):
        lines = ["手动下载模型（不想用内置下载时）：",
                 "",
                 "方法一：命令行运行随包脚本（需 Python 环境）",
                 "  python 下载模型.py faster-whisper-medium",
                 "",
                 "方法二：浏览器从 ModelScope 下载后解压到 models\\ 文件夹",
                 "  需包含：config.json / model.bin / tokenizer.json / vocabulary.txt 等",
                 ""]
        for name, src in MODEL_SOURCES.items():
            lines.append(f"· {name}: {src['url']}")
        QMessageBox.information(self, "手动下载说明", "\n".join(lines))

    # ------------------------------------------------------------ 按钮行为
    def _open_models_folder(self):
        path = models_dir(self.base_dir)
        os.makedirs(path, exist_ok=True)
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "无法打开", f"打不开模型文件夹：{e}\n路径：{path}")

    def _open_prompt_folder(self):
        """打开提示词_config.json 所在文件夹并高亮该文件（.json 可能无默认程序打开）。"""
        path = prompt_config.config_path(self.base_dir)
        try:
            subprocess.Popen(["explorer", "/select,", path])
        except Exception as e:
            QMessageBox.warning(self, "无法打开", f"打不开文件夹：{e}\n路径：{path}")

    def _restore_defaults(self):
        ret = QMessageBox.question(
            self, "恢复默认",
            "确定要把所有设置（含提示词模板内容）恢复为默认吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        self.cfg.data = dict(DEFAULT_CONFIG)
        self.cfg.save()
        prompt_config.restore_defaults(self.base_dir)
        self.font_size = DEFAULT_CONFIG["font"]
        self.alpha = DEFAULT_CONFIG["alpha"]
        # 刷新全部控件
        self._populate_devices()
        self.compute.setCurrentText(DEFAULT_CONFIG["device"])
        self.silence.setValue(DEFAULT_CONFIG["silence_ms"])
        self.beam.setValue(DEFAULT_CONFIG["beam"])
        self.merge.setChecked(DEFAULT_CONFIG["merge"])
        self.stream.setValue(DEFAULT_CONFIG["stream_ms"])
        self.font.setValue(DEFAULT_CONFIG["font"])
        self.opacity.setValue(DEFAULT_CONFIG["alpha"])
        self._populate_model_combo()
        self._populate_prompt_combo()
        self._refresh_dl_combo()
        QMessageBox.information(self, "恢复默认", "已恢复全部默认设置。")

    def _apply(self):
        c = self.cfg
        c.set("model", self.model_combo.currentText())
        c.set("device", self.compute.currentText())
        c.set("device_index", self.device_combo.currentData())
        c.set("silence_ms", self.silence.value())
        c.set("beam", self.beam.value())
        c.set("merge", self.merge.isChecked())
        c.set("stream_ms", self.stream.value())
        c.set("font", self.font.value())
        c.set("alpha", self.opacity.value())
        prompt_config.set_active(self.base_dir, self.prompt_combo.currentText())

        self.font_size = self.font.value()
        self.alpha = self.opacity.value()
        self.accept()
