@echo off
rem ============================================================
rem Ai_EchoSub · 实时中文字幕   Author: JIE-ONE5926
rem ============================================================
chcp 65001 >nul
title Ai_EchoSub 打包
cd /d "%~dp0"

set "ROOT=%~dp0.."
set "DIST=%ROOT%\dist\Ai_EchoSub"

if not exist "%ROOT%\venv\Scripts\python.exe" (
  echo [错误] 找不到 venv\Scripts\python.exe，请先创建虚拟环境并安装依赖
  pause
  exit /b 1
)

echo == 1/6 运行 PyInstaller 打包 ==
"%ROOT%\venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "%ROOT%\build\Ai_EchoSub.spec"
if errorlevel 1 (
  echo [错误] PyInstaller 打包失败
  pause
  exit /b 1
)

echo == 2/6 拷贝模型到 dist\Ai_EchoSub\models ==
if exist "%ROOT%\models\faster-whisper-large-v3-turbo" (
  xcopy /e /i /y "%ROOT%\models\faster-whisper-large-v3-turbo" "%DIST%\models\faster-whisper-large-v3-turbo\" >nul
  echo   ✓ 已拷贝 faster-whisper-large-v3-turbo
) else (
  echo   [提示] 项目 models 目录为空，首次运行 exe 时会自动下载
)

echo == 3/6 拷贝图标与随包资源到 dist ==
if exist "%ROOT%\图标.png"   xcopy /y "%ROOT%\图标.png"   "%DIST%\" >nul
if exist "%ROOT%\图标.jpg"   xcopy /y "%ROOT%\图标.jpg"   "%DIST%\" >nul
if exist "%ROOT%\图标.ico"   xcopy /y "%ROOT%\图标.ico"   "%DIST%\" >nul
if exist "%ROOT%\assets"     xcopy /e /i /y "%ROOT%\assets" "%DIST%\assets\" >nul
if exist "%ROOT%\下载模型.py" xcopy /y "%ROOT%\下载模型.py" "%DIST%\" >nul

echo == 4/6 创建字幕记录目录 ==
if not exist "%DIST%\字幕记录" mkdir "%DIST%\字幕记录"

echo == 5/6 复制成品到项目根目录（双击 %ROOT%\Ai_EchoSub.exe 即用） ==
xcopy /e /i /y "%DIST%\" "%ROOT%\" >nul

echo == 6/6 完成 ==
echo.
echo 产物：
echo   ① %DIST%\Ai_EchoSub.exe （dist 内副本）
echo   ② %ROOT%\Ai_EchoSub.exe  （项目根目录，直接双击可用）
echo.
pause
