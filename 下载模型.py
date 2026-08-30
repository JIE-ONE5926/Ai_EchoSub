# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""手动下载模型脚本（备用入口）。

用法：
  venv/Scripts/python 下载模型.py faster-whisper-medium
  可选：faster-whisper-large-v3-turbo / faster-whisper-large-v3 / faster-whisper-medium
断点续传：中断后重跑即可续传。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.download import download_model  # noqa: E402

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "faster-whisper-medium"
    base = os.path.dirname(os.path.abspath(__file__))
    print(f"下载模型：{name}", flush=True)
    ok = download_model(
        base, name,
        progress_cb=lambda s, d, t, sp: print(
            f"\r{s}  {d:.0f}/{t:.0f}MB  {sp:.1f}MB/s", end="", flush=True))
    print(flush=True)
    print("下载成功 ✓" if ok else "下载未完成（重跑可续传）", flush=True)
    sys.exit(0 if ok else 1)
