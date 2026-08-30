# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
音频采集模块：WASAPI 环回采集系统声音 + 能量断句。

纯 Python，不依赖 UI。
"""
import queue
import threading
import time

import numpy as np

TARGET_RATE = 16000
BLOCK_MS = 100


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """线性插值重采样到 16kHz。"""
    if sr_in == sr_out or len(x) == 0:
        return x.astype(np.float32)
    n_out = max(1, int(len(x) * sr_out / sr_in))
    idx = np.arange(n_out) * (sr_in / sr_out)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


class Segmenter:
    """按能量把连续声音切成一句一句（停顿 sil_end_ms 即断句，默认 400ms）。"""

    def __init__(self, rate=TARGET_RATE, sil_end_ms=400, max_ms=9000):
        self.rate = rate
        self.sil_end_ms = sil_end_ms
        self.max_len = int(rate * max_ms / 1000)
        self.lock = threading.Lock()
        self.buf = []
        self.buf_len = 0
        self.in_speech = False
        self.sil_ms = 0
        self.noise = 1e-3
        self.pre = int(0.25 * rate)  # 语音开始前保留的预滚长度

    def feed(self, block: np.ndarray):
        with self.lock:
            segs = []
            rms = float(np.sqrt(np.mean(block ** 2) + 1e-12))
            if not self.in_speech:
                # 只有真正安静的时候才更新底噪，避免语音被误计为噪声抬高阈值
                if rms < max(self.noise * 3, 0.006):
                    self.noise = 0.9 * self.noise + 0.1 * max(rms, 1e-4)
                if rms > max(self.noise * 6, 0.004):
                    self.in_speech = True
                    self.sil_ms = 0
            else:
                if rms < max(self.noise * 4, 0.003):
                    self.sil_ms += BLOCK_MS
                else:
                    self.sil_ms = 0

            self.buf.append(block)
            self.buf_len += len(block)

            if not self.in_speech:
                self._trim_pre()

            if self.in_speech and (self.sil_ms >= self.sil_end_ms or self.buf_len >= self.max_len):
                seg = self._take()
                self.in_speech = False
                self.sil_ms = 0
                if len(seg) > int(0.35 * self.rate):
                    segs.append(seg)
                else:
                    self.buf, self.buf_len = [], 0
        return segs

    def flush(self):
        with self.lock:
            if self.in_speech and self.buf_len > int(0.35 * self.rate):
                return self._take()
        return None

    def peek(self):
        """当前正在说的这段声音（还没断句的部分），供"边说边出字"预览转写。"""
        with self.lock:
            if not self.in_speech or not self.buf:
                return None
            return np.concatenate(self.buf).astype(np.float32)

    def _trim_pre(self):
        while self.buf and self.buf_len - len(self.buf[0]) > self.pre:
            self.buf_len -= len(self.buf.pop(0))

    def _take(self):
        seg = np.concatenate(self.buf) if self.buf else np.zeros(0, np.float32)
        self.buf, self.buf_len = [], 0
        # 结尾静音只保留 150ms
        cut_ms = self.sil_ms - 150
        if cut_ms > 0:
            cut = int(cut_ms / 1000 * self.rate)
            if 0 < cut < len(seg):
                seg = seg[: len(seg) - cut]
        return seg.astype(np.float32)


class LoopbackRecorder(threading.Thread):
    """环回采集系统声音：不占用、不改变正常的声音输出。"""

    def __init__(self, seg_q: queue.Queue, device_index=None, sil_end_ms=600):
        super().__init__(daemon=True)
        self.seg_q = seg_q
        self.device_index = device_index
        self.stop_evt = threading.Event()
        self.level = 0.0
        self.source_name = ""
        self._seg = Segmenter(TARGET_RATE, sil_end_ms=sil_end_ms)
        self.pa = None
        self.stream = None
        self.src_rate = 48000
        self.src_ch = 2
        self.block_frames = 4800
        # 供 UI 显示的采集状态
        self.status_cb = None  # callable(level: float) 可选

    def _open(self):
        import pyaudiowpatch as pyaudio
        if self.pa is None:
            self.pa = pyaudio.PyAudio()
        if self.device_index is not None:
            dev = self.pa.get_device_info_by_index(int(self.device_index))
            channels = int(dev.get("maxOutputChannels") or 2)
            rate = int(dev.get("defaultSampleRate") or 48000)
            kwargs = dict(as_loopback=True)
        else:
            try:
                dev = self.pa.get_default_wasapi_loopback()
                channels = int(dev.get("maxInputChannels") or 2)
                rate = int(dev.get("defaultSampleRate") or 48000)
                kwargs = {}
            except Exception:
                dev = self.pa.get_default_output_device_info()
                channels = int(dev.get("maxOutputChannels") or 2)
                rate = int(dev.get("defaultSampleRate") or 48000)
                kwargs = dict(as_loopback=True)
        self.source_name = dev.get("name", "")
        self.src_rate, self.src_ch = rate, channels
        self.block_frames = max(256, int(rate * BLOCK_MS / 1000))
        self.stream = self.pa.open(
            format=pyaudio.paInt16, channels=channels, rate=rate,
            input=True, output=False,
            input_device_index=int(dev["index"]),
            frames_per_buffer=self.block_frames, **kwargs)
        print(f"[音频] 正在监听系统声音：{self.source_name} "
              f"({rate}Hz,{channels}声道)", flush=True)

    def run(self):
        try:
            self._open()
        except Exception as e:
            print(f"[错误] 无法打开环回采集：{e}", flush=True)
            self.seg_q.put(None)
            return
        while not self.stop_evt.is_set():
            try:
                data = self.stream.read(self.block_frames, exception_on_overflow=False)
            except Exception as e:
                print(f"[音频] 流中断({e})，1秒后重试…", flush=True)
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
                time.sleep(1.0)
                try:
                    self._open()
                    continue
                except Exception:
                    time.sleep(2.0)
                    continue
            if not data:
                continue
            pcm = np.frombuffer(data, np.int16).astype(np.float32) / 32768.0
            if self.src_ch > 1:
                pcm = pcm.reshape(-1, self.src_ch).mean(axis=1)
            block = resample(pcm, self.src_rate, TARGET_RATE)
            self.level = float(np.sqrt(np.mean(block ** 2) + 1e-12))
            if self.status_cb:
                try:
                    self.status_cb(self.level)
                except Exception:
                    pass
            for seg in self._seg.feed(block):
                self.seg_q.put((seg, False))  # (音频, is_preview=False)：最终整句
        tail = self._seg.flush()
        if tail is not None:
            self.seg_q.put((tail, False))

    def stop(self):
        self.stop_evt.set()


def get_output_devices():
    """返回 (默认监听设备名, 输出设备列表)。设备项 = (index, name, sample_rate)。"""
    import pyaudiowpatch as pyaudio
    pa = pyaudio.PyAudio()
    default_name = ""
    try:
        default_name = pa.get_default_wasapi_loopback()["name"]
    except Exception:
        try:
            default_name = pa.get_default_output_device_info()["name"]
        except Exception:
            pass
    devices = []
    try:
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d.get("maxOutputChannels", 0) > 0 and not d.get("isLoopbackDevice"):
                devices.append((int(d["index"]), d["name"], int(d.get("defaultSampleRate") or 48000)))
    finally:
        pa.terminate()
    return default_name, devices


def list_output_devices():
    """打印所有输出设备编号（--list-devices 用）。"""
    default_name, devices = get_output_devices()
    print(f"== 默认监听设备：{default_name or '获取失败'}")
    print("\n== 所有输出设备（config.json 里 device_index 填编号可指定监听对象）==")
    for idx, name, rate in devices:
        mark = "  ◀ 当前默认" if name == default_name else ""
        print(f"  [{idx}] {name} ({rate}Hz){mark}")
