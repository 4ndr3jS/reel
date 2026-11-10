@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or later is required. Install it from https://www.python.org/downloads/ and add it to PATH.
  pause
  exit /b 1
)
python engine\launcher.py
if errorlevel 1 (
  echo.
  echo REEL could not start. See the message above.
)
pause
