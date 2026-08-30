# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
首次启动引导：环境检测 → 模型缺失则下载 → 加载模型。
"""
import threading

from src.download import download_model, model_ready, models_dir
from src.engine.transcriber import cuda_device_count
from src.ui.bootstrap_dialog import BootstrapDialog, ProgressBridge


def run_bootstrap(controller) -> bool:
    """返回是否继续进入主窗口。"""
    cfg = controller.config
    base_dir = controller.base_dir
    model_name = cfg.get("model")

    gpu_ok = cuda_device_count() > 0
    root = models_dir(base_dir)
    need_download = not model_ready(root, model_name)
    if need_download:
        print(f"[引导] 模型缺失/不完整：{model_name}，开始下载…", flush=True)

    dlg = BootstrapDialog(model_name, gpu_ok)
    bridge = ProgressBridge()
    bridge.finished.connect(dlg.on_finished)

    # ---- 1. 下载（如需要）----
    if need_download:
        dlg.phase_download()
        cancel_evt = threading.Event()
        bridge.progress.connect(dlg.on_progress)

        def _dl_worker():
            try:
                ok = download_model(
                    base_dir, model_name,
                    progress_cb=lambda s, d, t, sp: bridge.progress.emit(s, d, t, sp),
                    cancel_evt=cancel_evt)
                bridge.finished.emit(ok, "模型下载完成" if ok else "模型下载未完成")
            except Exception as e:
                bridge.finished.emit(False, f"下载失败：{e}")

        threading.Thread(target=_dl_worker, daemon=True).start()
        if dlg.exec() != 1:          # 用户取消
            return False

    # ---- 2. 加载模型 ----
    dlg.phase_loading()
    if need_download:
        bridge.progress.disconnect(dlg.on_progress)

    def _load_cb(ok: bool, _msg: str):
        bridge.finished.emit(ok, "模型加载失败" if not ok else "")

    controller.ensure_transcriber(callback=_load_cb)
    result = dlg.exec()
    if result != 1:
        return False
    return True
