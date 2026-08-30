# Ai_EchoSub · 实时中文字幕

实时把电脑正在播放的声音转成简体中文字幕，悬浮置顶显示。全程离线、不上传，
适合看视频 / 直播 / 会议回放时边看边出字幕，并自动保存记录用于复习。

**Author: JIE-ONE5926**

## 项目由来

作者平时会看一些**加密视频**，必须用特定的加密软件播放，但遇到几个痛点：

- 加密视频**没有字幕**，看起来比较吃力；
- 这个加密软件**不能录屏**，所以也没法用"录屏 + 语音识别"的方式出字幕；
- 用 PotPlayer 之类的播放器也无法直接打开这些加密视频，**自然也生成不了字幕**；

所以"出此下策"，做了这个**实时听写字幕工具**：不碰视频文件、不录屏、不上传，
只是把电脑正在播放的声音在本地实时转成文字，悬浮显示出来。

如果你有更好的方案，欢迎各位大佬指点，感谢！🙏

## 下载

- **全量版**（含模型，开箱即用）：见本仓库 **Releases**（`v1.0.0`）
- **无模型版**（体积小，首次运行自动下载模型）：见本仓库 **Releases**（`v1.0.0-lite`）

## 功能特性

- 🎙️ 环回采集系统声音（WASAPI loopback）：不占用、不改变正常输出，不碰视频文件与播放器
- 🧠 本地 faster-whisper 离线转写，支持 NVIDIA GPU(CUDA) 加速，无 GPU 自动回退 CPU
- 🪟 置顶悬浮字幕窗：可拖动、缩放、调字号 / 透明度；也可切换为主窗口内显示
- 🧩 句子平滑合并：碎片字幕自动拼成完整句
- 🛡️ 防幻觉：黑名单过滤 + 提示词回显检测 + 静音抑制
- 📂 字幕记录自动按天归档，方便复习
- 🌐 模型外置，首次运行自动从 ModelScope 下载（断点续传）；内置多档模型适配不同硬件

## 快速开始

### 方式一：直接运行 exe（推荐）

双击 `Ai_EchoSub.exe` 即可。首次运行会自动检测环境（GPU / 模型），缺失的模型自动下载。

### 方式二：从源码运行

```bat
:: 创建虚拟环境（Python 3.12）
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

:: 启动
venv\Scripts\python src\main.py
```

其他命令：

```bat
venv\Scripts\python src\main.py --selftest 20    :: 无界面自测（期间播放音频）
venv\Scripts\python src\main.py --list-devices   :: 列出输出设备
```

## 打包成 exe

```bat
build\build.bat
```

产物在 `dist\Ai_EchoSub\`：`Ai_EchoSub.exe` + `_internal\`（Python 运行时与全部依赖，无控制台窗口）。
模型不打包进 exe，外置于 `models\`，首次运行自动下载。

## 模型说明

| 模型 | 体积 | 适合配置 |
|---|---|---|
| faster-whisper-tiny | 75 MB | 低配 / CPU |
| faster-whisper-base | 145 MB | CPU |
| faster-whisper-small | 462 MB | 轻量 |
| faster-whisper-medium | 1.4 GB | 中配 |
| faster-whisper-large-v3 | 2.9 GB | 追求准确率 |
| faster-whisper-large-v3-turbo | 1.5 GB | 默认（GPU 快，准确率高） |

默认使用 `large-v3-turbo`，可在设置中切换模型或一键下载。

## 目录结构

```
├─ src\            源代码（PySide6 界面 + 采集 / 转写引擎）
├─ assets\         vocabulary.txt / preprocessor_config.json（模型下载兜底资源）
├─ build\          PyInstaller 打包配置（Ai_EchoSub.spec + build.bat）
├─ icon\           应用图标源文件（icon.PNG / icon.ico）
├─ 下载模型.py      手动下载模型脚本
└─ requirements.txt
```

## 隐私与数据

- **全程离线**：音频与字幕只在本地处理，不上传任何内容
- 字幕记录保存在本机 `字幕记录\<日期>\` 文件夹，可随时删除
- 运行日志（诊断用）在 `logs\Ai_EchoSub.log`，与字幕记录无关，可删除

## 依赖与致谢

- 识别引擎：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)（基于 CTranslate2 / OpenAI Whisper）
- 音频采集：[PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)（WASAPI loopback）
- 界面：PySide6 (Qt)

**Author: JIE-ONE5926**
