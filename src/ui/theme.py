# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""暗色主题：颜色与全局 QSS。"""

# 配色
BG       = "#101014"   # 窗口底色
BG_2     = "#1b1b22"   # 面板/控件底色
BG_3     = "#26262f"   # hover
LINE     = "#2c2c36"   # 分隔线
TEXT     = "#f0f0f3"   # 主文字
DIM      = "#8f8f9a"   # 次要文字
ACCENT   = "#3b82f6"   # 主题蓝
ACCENT_H = "#4f93ff"
GREEN    = "#34d399"   # 运行中
RED      = "#f87171"   # 停止/错误
BTN_TXT  = "#e8e8ee"

FONT_FAMILY = "Microsoft YaHei UI"

QSS = f"""
* {{
    font-family: "{FONT_FAMILY}";
    font-size: 13px;
    color: {TEXT};
}}
QWidget {{
    background: {BG};
}}
QLabel {{
    background: transparent;
}}
QPushButton {{
    background: {BG_2};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 7px 18px;
    color: {TEXT};
}}
QPushButton:hover {{
    background: {BG_3};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: #33333d;
}}
QPushButton:disabled {{
    color: {DIM};
    border-color: {LINE};
}}
QPushButton#primary {{
    background: {ACCENT};
    color: white;
    border: none;
}}
QPushButton#primary:hover {{
    background: {ACCENT_H};
}}
QPushButton#danger {{
    color: {RED};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {BG_2};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 5px 8px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG_2};
    border: 1px solid {LINE};
    selection-background-color: {ACCENT};
}}
QListWidget, QTextBrowser {{
    background: {BG};
    border: none;
    border-top: 1px solid {LINE};
}}
QScrollArea {{
    background: {BG};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: {BG};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a44;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4a4a56;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3a44;
    border-radius: 4px;
    min-width: 30px;
}}
QToolTip {{
    background: {BG_2};
    color: {TEXT};
    border: 1px solid {LINE};
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
}}
QDialog {{
    background: {BG};
}}
QMenu {{
    background: {BG_2};
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {LINE};
    margin: 4px 8px;
}}
QProgressBar {{
    background: {BG_2};
    border: 1px solid {LINE};
    border-radius: 6px;
    text-align: center;
    color: {DIM};
    height: 18px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}
"""
