# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
句子平滑合并：把断句产生的碎片字幕按"是否完整句"拼成整句。

规则：
  - 上句没以句号类结尾、新句也不完整 → 拼在一起继续等；
  - 太短的碎片（像是没说完整的开头，如"我们开始今天的"）在完整句到来时丢弃；
  - 超长/超时强制定稿，避免一直挂着。
"""


class SentenceMerger:
    ENDS = ("。", "！", "？", "……", "…", ".")

    def __init__(self, max_len=60, discard_len=12, timeout=8.0):
        self.buf = ""
        self.start = 0.0
        self.max_len = max_len
        self.discard_len = discard_len
        self.timeout = timeout

    @staticmethod
    def _join(a, b):
        # 中英交界：两个拉丁字母紧邻时补空格，避免 "Burp"+"Suite" 变 "BurpSuite"
        if a and b and a[-1].isascii() and a[-1].isalpha() \
                and b[0].isascii() and b[0].isalpha():
            return a + " " + b
        return a + b

    def feed(self, text, now):
        """送入一段识别结果，返回 (定稿句 or None, 当前应展示的文本)。"""
        text = text.strip()
        if not self.buf:
            self.buf, self.start = text, now
            return None, self.buf
        if self.buf.endswith(self.ENDS):            # 上一句已完整 → 定稿，开新句
            out, self.buf = self.buf, text
            self.start = now
            return out, self.buf
        if text.endswith(self.ENDS):                # 新句完整
            if len(self.buf) <= self.discard_len:   # 之前是句残片 → 丢弃，只留完整句
                self.buf, self.start = "", now
                return text, text
            out = self._join(self.buf, text)
            self.buf, self.start = "", now
            return out, text
        if len(self.buf) + len(text) <= self.max_len:  # 两段都不完整 → 拼起来
            self.buf = self._join(self.buf, text)
            return None, self.buf
        out, self.buf = self.buf, text
        self.start = now
        return out, self.buf

    def flush(self):
        if self.buf:
            out, self.buf = self.buf, ""
            return out
        return None

    def maybe_timeout(self, now):
        if self.buf and now - self.start > self.timeout:
            return self.flush()
        return None
