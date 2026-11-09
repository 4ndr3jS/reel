@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or later is required. Install it from python.org and add it to PATH.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is required. Install it with: winget install Gyan.FFmpeg
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js 22 or later is required. Install it from nodejs.org.
  pause
  exit /b 1
)
if not exist "engine\.deps\curl_cffi" (
  python -m pip install --disable-pip-version-check --target "engine\.deps" -r "engine\requirements.txt"
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
echo.
echo REEL - Keep the good stuff.
echo Open https://reel-download-studio-9nov.ampledulse1.chatgpt.site
echo.
python engine\server.py
pause
