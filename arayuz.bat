@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Kaynaktan (Python ile) arayuzu acar. Hazir .exe kullanacaksaniz buna
REM gerek yoktur; .exe ana yoldur, bu gelistirici/yedek yoldur.

if not exist ".venv\Scripts\pythonw.exe" (
  echo HATA: Once kur.bat dosyasini calistirin.
  pause
  exit /b 1
)

REM pythonw = konsol penceresi acmadan GUI baslatir
start "" ".venv\Scripts\pythonw.exe" -m perfetti_splitter.gui
