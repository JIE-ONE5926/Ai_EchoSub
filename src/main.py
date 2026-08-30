# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
Ai_EchoSub 桌面版入口。

启动流程：解析参数 → 初始化配置 → 首次启动引导（环境检测/模型下载/模型加载）
          → 主窗口（PySide6）。
"""
import argparse
import os
import sys

# 确保以项目根目录为运行基准
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def app_root() -> str:
    """数据目录：打包后 = exe 所在目录（models/ 字幕记录/ 在 exe 旁边）；开发 = 项目根。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _ROOT


def parse_args():
    ap = argparse.ArgumentParser(description="Ai_EchoSub 实时中文字幕（桌面版）")
    ap.add_argument("--skip-bootstrap", action="store_true",
                    help="跳过环境检测/模型下载引导，直接进主窗口")
    ap.add_argument("--selftest", type=int, default=0, metavar="秒",
                    help="无界面自测：采集 N 秒系统声音并转写（期间请播放音频）")
    ap.add_argument("--list-devices", action="store_true",
                    help="列出输出设备")
    ap.add_argument("--smoke", type=int, default=0, metavar="秒",
                    help=argparse.SUPPRESS)
    return ap.parse_args()


def _setup_output(base_dir: str):
    """PyInstaller 窗口模式（无控制台）下 sys.stdout 为 None，重定向到 logs\\Ai_EchoSub.log。
    注意：这只是运行日志（诊断用，可随时删除），与字幕记录（字幕记录\\日期\\）无关。"""
    if sys.stdout is None:
        log_dir = os.path.join(base_dir, "logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
            f = open(os.path.join(log_dir, "Ai_EchoSub.log"), "a", encoding="utf-8")
            sys.stdout = f
            sys.stderr = f
        except Exception:
            pass
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _resolve_icon(base_dir: str):
    """返回图标路径：打包后优先用内置在 exe 里的 icon.ico（ASCII 名，稳定），
    否则找根目录 图标.* / build/icon.ico / icon.ico（后两者 ASCII 名，防中文名文件被删）。"""
    if getattr(sys, "frozen", False):
        p = os.path.join(getattr(sys, "_MEIPASS", base_dir), "icon.ico")
        if os.path.isfile(p):
            return p
    for name in ("图标.png", "图标.jpg", "图标.ico"):
        p = os.path.join(base_dir, name)
        if os.path.isfile(p):
            return p
    for rel in (os.path.join("build", "icon.ico"), "icon.ico"):
        p = os.path.join(base_dir, rel)
        if os.path.isfile(p):
            return p
    return None


def main():
    args = parse_args()
    base_dir = app_root()
    _setup_output(base_dir)

    if args.list_devices:
        from src.engine.recorder import list_output_devices
        list_output_devices()
        return 0

    if args.selftest:
        from src.selftest import run_selftest
        return run_selftest(base_dir, args.selftest)

    from PySide6.QtWidgets import QApplication

    from src.app import AppController
    from src.bootstrap import run_bootstrap
    from src.config import Config
    from src.ui.theme import QSS

    config = Config(base_dir)
    app = QApplication(sys.argv)
    app.setApplicationName("Ai_EchoSub")
    app.setStyleSheet(QSS)

    # 应用/任务栏图标：与 exe 文件图标一致（打包后内置 icon.ico，开发环境用根目录 图标.*）
    from PySide6.QtGui import QIcon
    icon_path = _resolve_icon(base_dir)
    app_icon = QIcon(icon_path) if icon_path else QIcon()
    if icon_path:
        app.setWindowIcon(app_icon)

    controller = AppController(config, base_dir)

    if not args.skip_bootstrap:
        if not run_bootstrap(controller):
            return 1

    from src.ui.main_window import MainWindow
    win = MainWindow(controller)
    if icon_path:
        win.setWindowIcon(app_icon)   # 任务栏图标与 exe 图标一致
    win.show()

    if args.smoke:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(int(args.smoke * 1000), win._really_quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
