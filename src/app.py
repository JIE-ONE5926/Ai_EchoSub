# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
应用控制器：连接引擎与界面，管理运行状态、字幕分发、字幕记录。

引擎层（src/engine）保持纯逻辑；本模块是唯一同时接触引擎和 UI 的桥。
"""
import os
import queue
import threading
import time
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from src import prompt_config
from src.config import Config
from src.engine.merger import SentenceMerger
from src.engine.recorder import LoopbackRecorder
from src.engine.transcriber import Transcriber, cuda_device_count, stream_loop


class TranscriptLog:
    """字幕记录：存到 字幕记录(按天分文件夹) 下的 字幕记录_日期_时间.txt。"""

    def __init__(self, folder: str):
        date = datetime.now().strftime("%Y-%m-%d")
        subdir = os.path.join(folder, "字幕记录", date)
        os.makedirs(subdir, exist_ok=True)
        self.path = os.path.join(subdir, f"字幕记录_{datetime.now():%Y-%m-%d_%H%M}.txt")
        self.lock = threading.Lock()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"==== {datetime.now():%Y-%m-%d %H:%M:%S} 开始 ====\n")

    def add(self, text: str):
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%H:%M:%S}] {text}\n")


class AppController(QObject):
    # ---- UI 信号 ----
    caption = Signal(str, str)        # (上一句, 当前句)：主窗口与悬浮窗共同消费
    preview = Signal(str)             # 边说边出字预览（只刷当前句）
    history_added = Signal(str)       # 一句定稿：写入历史区与记录文件
    state_changed = Signal(bool)      # 采集/识别是否运行中
    status = Signal(str)              # 状态条文案
    device_info = Signal(str)         # 设备信息：GPU(CUDA) / CPU + 模型名
    audio_level = Signal(float)       # 当前音量（0~1，供电平条）
    model_ready = Signal(bool)        # 模型加载完成/失败

    def __init__(self, config: Config, base_dir: str):
        super().__init__()
        self.config = config
        self.base_dir = base_dir
        self.log = TranscriptLog(base_dir)

        self.transcriber: Transcriber = None
        self.recorder: LoopbackRecorder = None
        self.job_q = queue.Queue()
        self.text_q = queue.Queue()
        self.stop_evt = threading.Event()
        self.worker_thread = None
        self.stream_thread = None

        self.running = False
        self.loading = False          # 正在加载/重载模型
        self.last_final = ""
        self.last_caption_t = time.time()
        self._merger = None
        self.loaded_model_name = None
        self.loaded_prompt = ""

    # ------------------------------------------------------------ 环境
    @property
    def device_label(self) -> str:
        dev = self.config.get("device", "auto")
        if dev == "auto":
            return "GPU (CUDA)" if cuda_device_count() > 0 else "CPU"
        return "GPU (CUDA)" if dev == "cuda" else "CPU"

    def ensure_transcriber(self, callback=None):
        """确保模型已加载（按当前配置）。阻塞调用，勿在 UI 线程直接调用。
        callback(success: bool, message: str) 在线程内回调。"""
        self.loading = True
        self.status.emit("正在加载模型…")

        def _work():
            ok, msg = False, ""
            try:
                cfg = self.config
                self.loaded_prompt = prompt_config.get_active_prompt(self.base_dir)
                self.transcriber = Transcriber(
                    self.base_dir, cfg.get("model"),
                    device=cfg.get("device", "auto"),
                    compute=cfg.get("compute", "auto"),
                    lang=cfg.get("lang", "zh"),
                    beam_size=cfg.get("beam", 5),
                    prompt=self.loaded_prompt)
                self.loaded_model_name = cfg.get("model")
                ok = True
                msg = f"{self.transcriber.device}/{self.transcriber.compute}"
                self.device_info.emit(f"{self.device_label} · {cfg.get('model')}")
            except Exception as e:
                msg = f"模型加载失败：{e}"
                print(msg, flush=True)
            finally:
                self.loading = False
                self.model_ready.emit(ok)
                self.status.emit("模型就绪" if ok else "模型加载失败")
                if callback:
                    try:
                        callback(ok, msg)
                    except Exception:
                        pass

        threading.Thread(target=_work, daemon=True).start()

    # ------------------------------------------------------------ 运行
    def start(self):
        if self.running:
            return
        if self.transcriber is None:
            self.status.emit("模型未就绪，请先完成初始化")
            return

        self.last_final = ""
        self._merger = SentenceMerger() if self.config.get("merge", True) else None

        self.job_q = queue.Queue()
        self.text_q = queue.Queue()
        self.stop_evt = threading.Event()

        self.recorder = LoopbackRecorder(
            self.job_q, self.config.get("device_index"),
            self.config.get("silence_ms", 400))
        self.recorder.status_cb = lambda lv: self.audio_level.emit(lv)
        self.recorder.start()

        self.worker_thread = threading.Thread(
            target=self.transcriber.worker, args=(self.job_q, self.text_q), daemon=True)
        self.worker_thread.start()

        stream_ms = self.config.get("stream_ms", 0)
        if stream_ms:
            self.stream_thread = threading.Thread(
                target=stream_loop, daemon=True,
                args=(self.recorder._seg, self.job_q, self.stop_evt, stream_ms))
            self.stream_thread.start()

        self.running = True
        self.state_changed.emit(True)
        self.status.emit(f"正在监听：{self.recorder.source_name or '系统声音'}")

    def stop(self):
        if not self.running:
            return
        self.stop_evt.set()
        if self.recorder:
            self.recorder.stop()
        self.job_q.put(None)  # 结束识别线程
        self.running = False
        self.state_changed.emit(False)
        self.status.emit("已停止")

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    # ------------------------------------------------------------ 字幕分发
    def drain(self):
        """UI 定时轮询：取识别结果 → 合并 → 发信号。返回是否有新内容。"""
        got = False
        try:
            while True:
                text, is_preview = self.text_q.get_nowait()
                self._on_text(text, is_preview)
                got = True
        except queue.Empty:
            pass
        if self._merger is not None and not self.running:
            # 停止后把残留的半句定稿出来
            fin = self._merger.flush()
            if fin:
                self._emit_final(fin)
                got = True
        if self._merger is not None and self.running:
            fin = self._merger.maybe_timeout(time.time())
            if fin:
                self._emit_final(fin)
                got = True
        return got

    def _on_text(self, text, is_preview):
        if is_preview:
            self.preview.emit(text)
            return
        now = time.time()
        if self._merger is not None:
            finalized, show = self._merger.feed(text, now)
            if finalized:
                self._emit_final(finalized)
            self.caption.emit(self.last_final, show)
        else:
            self._emit_final(text)
        self.last_caption_t = now

    def _emit_final(self, text):
        prev = self.last_final
        self.last_final = text
        line = f"[{datetime.now():%H:%M:%S}] {text}"
        self.history_added.emit(line)
        self.log.add(text)
        print(line, flush=True)
        self.caption.emit(prev, text)

    # ------------------------------------------------------------ 设置
    def apply_settings(self):
        """设置变更后调用：停掉当前运行，按需重载模型（模型/提示词变了才重载）。"""
        was_running = self.running
        self.stop()
        prompt_changed = prompt_config.get_active_prompt(self.base_dir) != self.loaded_prompt
        if (self.transcriber is None
                or self.loaded_model_name != self.config.get("model")
                or prompt_changed):
            def _done(ok, _msg):
                if ok and was_running:
                    self.start()
            self.ensure_transcriber(callback=_done)
        elif was_running:
            self.start()

    def quit(self):
        try:
            self.stop()
        except Exception:
            pass
