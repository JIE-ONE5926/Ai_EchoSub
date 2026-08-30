# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
转写模块：faster-whisper 模型加载 / GPU 检测 / 转写线程 / 防幻觉。

纯 Python，不依赖 UI。
"""
import os
import queue
import threading
import time

# 已知 Whisper 中文幻觉句：large-v3 在纯音乐/背景音段常整句输出这类"求三连"话
HALLUC_PHRASES = (
    "请不吝点赞订阅转发打赏支持明镜与点点栏目",
    "点赞订阅转发",
    "明镜与点点",
    "求三连",
    "点赞评论订阅",
)
# 提示词里的独特标记，用于识别"把提示词当内容输出了"的走样回显
PROMPT_MARKERS = ("以下是", "讲课内容", "可能涉及", "专业术语")


def is_hallucination(text: str, prompt: str = "") -> bool:
    """判断识别结果是不是幻觉：①已知求三连句 ②提示词（走样）回显。"""
    for h in HALLUC_PHRASES:
        if h in text:
            return True
    if prompt:
        ttxt, ptxt = text.replace(" ", ""), prompt.replace(" ", "")
        if ttxt == ptxt or ttxt.startswith(ptxt):
            return True
        if sum(1 for m in PROMPT_MARKERS if m in ttxt) >= 2:
            return True
    return False


def cuda_device_count() -> int:
    """返回可用 CUDA 设备数（无 CUDA/加载失败返回 0）。"""
    try:
        import ctranslate2
        return int(ctranslate2.get_cuda_device_count() or 0)
    except Exception:
        return 0


def resolve_device(device: str) -> str:
    """--device=auto 时自动选 GPU(CUDA)，没有 CUDA 就回退 CPU。"""
    if device != "auto":
        return device
    return "cuda" if cuda_device_count() > 0 else "cpu"


def resolve_compute(device: str, compute: str) -> str:
    """--compute=auto 时：GPU 用 int8_float16（大模型下比 float16 快约 5 倍），CPU 用 int8。"""
    if compute != "auto":
        return compute
    return "int8_float16" if device == "cuda" else "int8"


def resolve_model_path(base: str, name: str) -> str:
    if os.path.isdir(name):
        return name
    local = os.path.join(base, "models", name)
    if os.path.isfile(os.path.join(local, "model.bin")):
        return local
    return name  # 交给 huggingface（需要联网）


class Transcriber:
    """封装 WhisperModel 的加载与转写线程。"""

    def __init__(self, base_dir: str, model_name: str, device: str = "auto",
                 compute: str = "auto", lang: str = "zh", beam_size: int = 5,
                 prompt: str = "", cpu_threads: int = None):
        self.base_dir = base_dir
        self.model_name = model_name
        self.lang = lang
        self.beam_size = beam_size
        self.prompt = prompt
        self.device = resolve_device(device)
        self.compute = resolve_compute(self.device, compute)
        self.model = None
        self.load_time = 0.0
        self._load_model(cpu_threads or min(8, os.cpu_count() or 4))

    def _load_model(self, cpu_threads: int):
        from faster_whisper import WhisperModel
        path = resolve_model_path(self.base_dir, self.model_name)
        print(f"[模型] 加载中：{path}（{self.device}/{self.compute}，首次加载约需十几秒…）", flush=True)
        t0 = time.time()
        try:
            self.model = WhisperModel(path, device=self.device, compute_type=self.compute,
                                     cpu_threads=cpu_threads)
        except Exception as e:
            if self.device == "cuda":
                print(f"[模型] GPU 加载失败（{e}），回退到 CPU…", flush=True)
                self.device, self.compute = "cpu", resolve_compute("cpu", "auto")
                self.model = WhisperModel(path, device="cpu", compute_type=self.compute,
                                         cpu_threads=cpu_threads)
            else:
                raise
        self.load_time = time.time() - t0
        print(f"[模型] 就绪：{self.device}/{self.compute}，用时 {self.load_time:.1f}s", flush=True)

    def transcribe(self, seg, vad_parameters=None):
        """转写一段音频，返回识别文本（含防幻觉过滤）。"""
        gen, _ = self.model.transcribe(
            seg, language=self.lang, beam_size=self.beam_size,
            vad_filter=True,
            vad_parameters=vad_parameters or dict(min_silence_duration_ms=300),
            condition_on_previous_text=False,
            no_speech_threshold=0.4,          # 更积极丢弃"没说话"的段（含背景音乐）
            initial_prompt=self.prompt)
        text = "".join(s.text for s in gen).strip()
        if is_hallucination(text, self.prompt):
            text = ""
        if text and self.lang.lower() in ("zh", "chinese", "ch"):
            text = text.replace(" ", "")
        return text

    def worker(self, job_q: queue.Queue, text_q: queue.Queue):
        """统一识别线程：处理最终整句和流式预览，输出 (text, is_preview)。"""
        while True:
            job = job_q.get()
            if job is None:
                break
            seg, is_preview = job
            try:
                text = self.transcribe(seg)
            except Exception as e:
                print(f"[识别] 出错：{e}", flush=True)
                continue
            if text:
                text_q.put((text, is_preview))
        print("[识别] 已退出", flush=True)


def stream_loop(seg, job_q, stop_evt, interval_ms=800):
    """边说边出字：说话中每隔 interval_ms 把当前这段声音转一次（预览字幕）。
    只在队列空闲时投递，绝不挤占最终整句的转写。"""
    last = 0.0
    while not stop_evt.is_set():
        buf = seg.peek()
        if buf is not None:
            t = time.time()
            if t - last >= interval_ms / 1000.0 and job_q.qsize() < 1:
                last = t
                job_q.put((buf, True))  # (音频, is_preview=True)：实时预览
        time.sleep(0.1)
