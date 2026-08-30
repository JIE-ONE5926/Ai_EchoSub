# -*- mode: python ; coding: utf-8 -*-
# Ai_EchoSub · 实时中文字幕   Author: JIE-ONE5926
"""
Ai_EchoSub 打包配置（PyInstaller onedir）。
用法：cd build && ..\venv\Scripts\pyinstaller --noconfirm Ai_EchoSub.spec
产物：dist\Ai_EchoSub\Ai_EchoSub.exe（模型外置，见 build.bat 里的拷贝步骤）
"""
import os

from PyInstaller.utils.hooks import collect_all

project_root = os.path.dirname(os.path.dirname(SPEC))   # build/ 的上一级 = 项目根

datas, binaries, hiddenimports = [], [], []

# 这些包是运行时动态 import 的（faster_whisper / pyaudiowpatch / ctranslate2），
# PyInstaller 静态扫描不到，必须 collect_all 收全包内数据与 DLL。
for pkg in ("faster_whisper", "ctranslate2", "onnxruntime", "pyaudiowpatch"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# faster-whisper 在模块层 import av（音频解码），补收其 C 扩展（hooks-contrib 有 hook-av）
hiddenimports += ["av", "tokenizers", "huggingface_hub", "tqdm", "yaml", "ctranslate2"]

# 把图标打进包内（ASCII 名 icon.ico → _internal 根），运行时从 sys._MEIPASS 读取，
# 保证任务栏图标与 exe 图标一致且不受外部图标文件缺失影响
datas.append((os.path.join(project_root, "build", "icon.ico"), "."))

a = Analysis(
    [os.path.join(project_root, "src", "main.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ai_EchoSub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 无控制台窗口（产品化）；日志写入 Ai_EchoSub.log
    disable_windowed_traceback=False,
    icon=os.path.join(project_root, "build", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Ai_EchoSub",
)
