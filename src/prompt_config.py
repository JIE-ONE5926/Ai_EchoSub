# -*- coding: utf-8 -*-
# ============================================================
# Ai_EchoSub · 实时中文字幕
# Author: JIE-ONE5926
# ============================================================

"""
提示词配置文件：`提示词_config.json`（用户可自行编辑/新增模板）。

结构：
{
  "active": "网络安全",            ← 当前生效的模板名
  "templates": {                    ← 模板字典
    "网络安全": "以下是……专业术语。",
    "通用": "以下是简体中文普通话讲课内容。"
  }
}
"""
import json
import os

DEFAULT_TEMPLATES = {
    "网络安全": "以下是网络安全方向的简体中文普通话讲课内容，可能涉及：信息收集"
               "（子域名枚举、端口扫描、Nmap、指纹识别、目录扫描）、Web 漏洞"
               "（SQL 注入、XSS、CSRF、SSRF、XXE、文件上传、文件包含、命令执行、"
               "反序列化、目录遍历、越权、逻辑漏洞、弱口令、暴力破解、WAF 绕过）、"
               "常用工具（Burp Suite、SqlMap、Nuclei、Xray、Kali、Metasploit、Webshell）、"
               "内网与防护（CVE、POC、EXP、提权、内网渗透、横向移动、免杀、"
               "应急响应、日志分析）等专业术语。",
    "通用": "以下是简体中文普通话讲课内容。",
}

FILENAME = "提示词_config.json"


def config_path(base_dir: str) -> str:
    return os.path.join(base_dir, FILENAME)


def load(base_dir: str) -> dict:
    """读取提示词配置；文件缺失/损坏则用默认并写盘。默认生效模板为"通用"。"""
    data = {"active": "通用", "templates": dict(DEFAULT_TEMPLATES)}
    path = config_path(base_dir)
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            if isinstance(loaded.get("templates"), dict):
                data["templates"].update(loaded["templates"])
            if isinstance(loaded.get("active"), str) and loaded["active"] in data["templates"]:
                data["active"] = loaded["active"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    save(base_dir, data)
    return data


def save(base_dir: str, data: dict) -> None:
    try:
        with open(config_path(base_dir), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[提示词] 保存失败：{e}", flush=True)


def list_templates(base_dir: str) -> list[str]:
    return list(load(base_dir)["templates"].keys())


def get_active_prompt(base_dir: str) -> str:
    data = load(base_dir)
    return data["templates"].get(data["active"], "")


def set_active(base_dir: str, name: str) -> None:
    data = load(base_dir)
    if name in data["templates"]:
        data["active"] = name
        save(base_dir, data)


def restore_defaults(base_dir: str) -> None:
    """把提示词配置文件完全还原为默认（含模板内容），active 回到"通用"。"""
    save(base_dir, {"active": "通用", "templates": dict(DEFAULT_TEMPLATES)})
