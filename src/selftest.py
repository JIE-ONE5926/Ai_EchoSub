# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
无界面自测：采集 N 秒系统声音 → 断句 → 转写，打印音量与识别结果。
用法：python src/main.py --selftest 20
"""
import queue
import threading
import time

from src.config import Config
from src.engine.recorder import LoopbackRecorder
from src.engine.transcriber import Transcriber


def run_selftest(base_dir: str, seconds: int) -> int:
    cfg = Config(base_dir)
    print(f"[自测] 采集系统声音 {seconds} 秒，期间请播放任意音频…",
          flush=True)
    print(f"[自测] 模型：{cfg.get('model')}", flush=True)

    tr = Transcriber(base_dir, cfg.get("model"),
                     device=cfg.get("device", "auto"), compute=cfg.get("compute", "auto"),
                     lang=cfg.get("lang", "zh"), beam_size=cfg.get("beam", 5),
                     prompt=cfg.get("prompt", ""))
    job_q, text_q = queue.Queue(), queue.Queue()
    rec = LoopbackRecorder(job_q, cfg.get("device_index"), cfg.get("silence_ms", 400))
    rec.start()
    threading.Thread(target=tr.worker, args=(job_q, text_q), daemon=True).start()

    peak, n_seg = 0.0, 0
    t_end = time.time() + seconds
    while time.time() < t_end:
        time.sleep(0.5)
        bar = "#" * min(40, int(rec.level * 200))
        print(f"  音量 {bar:<40} {rec.level:.4f}", flush=True)
        peak = max(peak, rec.level)
        try:
            while True:
                text, _prev = text_q.get_nowait()
                n_seg += 1
                print(f"  [转写] {text}", flush=True)
        except queue.Empty:
            pass

    rec.stop()
    rec.join(timeout=3)
    job_q.put(None)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            text, _prev = text_q.get(timeout=0.5)
            n_seg += 1
            print(f"  [转写] {text}", flush=True)
        except queue.Empty:
            break

    print(f"[自测] 峰值音量 {peak:.4f}，识别出 {n_seg} 句", flush=True)
    if peak < 0.002:
        print("[自测] !! 基本没采到声音：请确认自测期间系统确实在播放音频，"
              "或用 --list-devices 检查输出设备", flush=True)
        return 1
    print("[自测] 声音采集正常 ✓", flush=True)
    return 0
