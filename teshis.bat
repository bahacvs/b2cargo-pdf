@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Perfetti Vardiya Ayirma - TESHIS
echo ============================================
echo.

REM Kurulum yapilmis mi?
if not exist ".venv\Scripts\python.exe" (
  echo HATA: Once kur.bat dosyasini calistirin.
  pause
  exit /b 1
)

REM Gelen klasorde PDF var mi?
dir /b "workdir\Gelen_PDF\*.pdf" >nul 2>nul
if errorlevel 1 (
  echo UYARI: workdir\Gelen_PDF klasorunde hic PDF bulunamadi.
  echo   Test ettiginiz irsaliye PDF'lerini bu klasore koyup tekrar deneyin.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" teshis.py

echo.
echo teshis.txt olusturuldu, aciliyor...
start "" "teshis.txt"
echo.
echo Bu dosyayi (teshis.txt) gelistiriciye gonderin.
echo.
pause
