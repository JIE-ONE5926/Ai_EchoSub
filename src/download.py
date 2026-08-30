# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
模型下载器：从 ModelScope 下载 faster-whisper 模型，支持断点续传（Range）。

带进度回调，供 UI 显示。
"""
import os
import shutil
import threading
import time
import urllib.request

from src.config import MODEL_SOURCES


def models_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "models")


def model_ready(models_root: str, model_name: str) -> bool:
    """检查模型是否已完整下载（model.bin 存在且达到目标大小）。"""
    src = MODEL_SOURCES.get(model_name)
    d = os.path.join(models_root, model_name)
    if not os.path.isdir(d):
        return False
    if not os.path.isfile(os.path.join(d, "model.bin")):
        return False
    if src:
        mb = os.path.getsize(os.path.join(d, "model.bin")) / 1e6
        if mb < src["model_bin_mb"] * 0.95:
            return False
    return True


def _ensure_optional_files(base_dir: str, dest_dir: str, models_root: str) -> None:
    """补充下载列表之外、但 ctranslate2 需要的文件（vocabulary.txt / preprocessor_config.json）。
    顺序：本地已有 → 从其他已下载模型复制 → 从随包 assets 资源复制。"""
    for name in ("vocabulary.txt", "preprocessor_config.json"):
        dst = os.path.join(dest_dir, name)
        if os.path.isfile(dst):
            continue
        copied = False
        for sub in os.listdir(models_root) if os.path.isdir(models_root) else []:
            src = os.path.join(models_root, sub, name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"  复制 {name}（从 {sub}）", flush=True)
                copied = True
                break
        if copied:
            continue
        # assets 资源兜底（随包分发，保证全新下载也能自足）
        asset = os.path.join(base_dir, "assets", name)
        if os.path.isfile(asset):
            shutil.copy2(asset, dst)
            print(f"  复制 {name}（从随包 assets）", flush=True)


def download_model(base_dir: str, model_name: str,
                   progress_cb=None, cancel_evt: threading.Event = None) -> bool:
    """下载指定模型到 models\\<model_name>。返回是否成功。

    progress_cb(status: str, percent: float, speed_mb_s: float)  每秒回调多次。
    cancel_evt 置位后中断（保留已下载部分，可续传）。
    """
    src = MODEL_SOURCES.get(model_name)
    if src is None:
        raise ValueError(f"未配置的模型下载源: {model_name}")

    root = models_dir(base_dir)
    dest = os.path.join(root, model_name)
    os.makedirs(dest, exist_ok=True)
    base_url = src["url"]

    total_mb = sum(
        (src["model_bin_mb"] if f == "model.bin" else 0.2) for f in src["files"])
    done_mb = 0.0
    ok = True

    def _report(status, speed=0.0):
        if progress_cb:
            try:
                progress_cb(status, done_mb, total_mb, speed)
            except Exception:
                pass

    for name in src["files"]:
        if cancel_evt is not None and cancel_evt.is_set():
            return False
        if not _dl_file(dest, base_url, name, src["model_bin_mb"] if name == "model.bin" else None,
                        _report, cancel_evt):
            ok = False
            break
        done_mb += src["model_bin_mb"] if name == "model.bin" else 0.2
        _report(f"完成 {name}")

    _ensure_optional_files(base_dir, dest, root)

    if ok and not model_ready(root, model_name):
        ok = False
    if not ok and progress_cb:
        progress_cb("下载中断或文件不完整，重试可续传", done_mb, total_mb, 0.0)
    return ok


def _dl_file(dest_dir, base_url, name, target_mb, report, cancel_evt, retries=8):
    dst = os.path.join(dest_dir, name)
    existing = os.path.getsize(dst) if os.path.isfile(dst) else 0
    if target_mb is None and existing > 0:
        print(f"  跳过(已存在): {name}", flush=True)
        return True
    if target_mb is not None and existing >= target_mb * 1e6:
        print(f"  跳过(已完整): {name} ({existing/1e6:.0f}MB)", flush=True)
        return True
    for attempt in range(1, retries + 1):
        try:
            headers = {"User-Agent": "curl/8"}
            if existing:
                headers["Range"] = f"bytes={existing}-"
            req = urllib.request.Request(base_url + name, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                status = getattr(r, "status", 200)
                mode = "wb"
                if existing and status == 206:
                    mode = "ab"
                elif existing:                      # 服务器不支持续传 → 重头下
                    existing = 0
                total = existing + int(r.headers.get("Content-Length") or 0)
                t0 = time.time()
                with open(dst, mode) as f:
                    while True:
                        if cancel_evt is not None and cancel_evt.is_set():
                            return False
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        existing += len(chunk)
                        if total:
                            mb = existing / 1e6
                            speed = mb / max(time.time() - t0, 0.01)
                            pct = existing / total * 100
                            report(f"下载 {name} ({pct:.0f}%)", speed)
            print(f"\r    {name} 完成 {existing/1e6:.0f}MB", flush=True)
            return True
        except Exception as e:
            existing = os.path.getsize(dst) if os.path.isfile(dst) else 0
            print(f"\n  {name} 第{attempt}次失败({e})，已下载{existing/1e6:.0f}MB，重试…", flush=True)
            if cancel_evt is not None and cancel_evt.is_set():
                return False
            time.sleep(2 * attempt)
    return False
