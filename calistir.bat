@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Perfetti Vardiya Ayirma - CALISTIR
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
  echo   Vardiya irsaliye PDF'lerini bu klasore kopyalayin ve tekrar deneyin.
  echo.
  pause
  exit /b 1
)

set /p VARDIYA="Vardiya adi (bos birakirsaniz otomatik tarih kullanilir): "

if "%VARDIYA%"=="" (
  ".venv\Scripts\python.exe" -m perfetti_splitter "workdir\Gelen_PDF"
) else (
  ".venv\Scripts\python.exe" -m perfetti_splitter "workdir\Gelen_PDF" --name "%VARDIYA%"
)

echo.
echo Cikti klasoru aciliyor...
start "" "workdir\Birlesik_PDF"
echo.
pause
