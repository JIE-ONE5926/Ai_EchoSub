# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
配置模块：config.json 读写，集中管理所有可调参数。
"""
import json
import os

DEFAULT_CONFIG = {
    # ---- 引擎 ----
    "model": "faster-whisper-large-v3-turbo",
    "lang": "zh",
    "device": "auto",            # auto/cuda/cpu
    "compute": "auto",           # auto/int8/float16/int8_float16
    "beam": 5,
    "silence_ms": 400,           # 停顿断句阈值
    "merge": True,               # 句子平滑合并
    "stream_ms": 0,              # 边说边出字间隔（0=关闭）
    # 领域提示词已迁移到 提示词_config.json（见 src/prompt_config.py）
    # ---- 界面 ----
    "font": 22,                  # 字幕字号
    "alpha": 0.82,               # 不透明度 0.3~0.98
    "subtitle_area_ratio": 0.35, # 主窗口字幕显示区占高度比例
    "window_width_ratio": 0.72,  # 主窗口占屏宽比例
    "overlay_ratio": 0.72,       # 悬浮字幕窗占屏宽比例
}

# 模型下载源（ModelScope，国内直连；每个模型一组文件）。
# 按硬件配置从小到大排列，供不同配置用户选择。
MODEL_SOURCES = {
    "faster-whisper-tiny": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-tiny/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin", "tokenizer.json",
                  "vocabulary.txt"],  # preprocessor_config.json 走复制兜底
        "model_bin_mb": 75,
    },
    "faster-whisper-base": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-base/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin", "tokenizer.json",
                  "vocabulary.txt"],  # preprocessor_config.json 走复制兜底
        "model_bin_mb": 145,
    },
    "faster-whisper-small": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-small/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin", "tokenizer.json",
                  "vocabulary.txt"],  # preprocessor_config.json 走复制兜底
        "model_bin_mb": 462,
    },
    "faster-whisper-medium": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-medium/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin", "tokenizer.json",
                  "vocabulary.txt"],  # preprocessor_config.json 走复制兜底
        "model_bin_mb": 1458,
    },
    "faster-whisper-large-v3": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-large-v3/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin", "tokenizer.json",
                  "vocabulary.json", "preprocessor_config.json"],  # vocabulary.txt 走复制兜底
        "model_bin_mb": 3000,
    },
    "faster-whisper-large-v3-turbo": {
        "url": "https://modelscope.cn/models/pengzhendong/faster-whisper-large-v3-turbo/resolve/master/",
        "files": ["config.json", "configuration.json", "model.bin",
                  "preprocessor_config.json", "tokenizer.json"],  # vocabulary.txt 走复制兜底
        "model_bin_mb": 1600,
    },
}


class Config:
    def __init__(self, base_dir: str, path: str = "config.json"):
        self.base_dir = base_dir
        self.path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update({k: v for k, v in loaded.items() if k in DEFAULT_CONFIG})
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[配置] 保存失败：{e}", flush=True)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
