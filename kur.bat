@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Perfetti Vardiya Ayirma - KURULUM
echo ============================================
echo.

REM 1) Python var mi?
where python >nul 2>nul
if errorlevel 1 (
  echo HATA: Python bulunamadi.
  echo   Once python.org adresinden Python kurun.
  echo   Kurulumda "Add Python to PATH" kutusunu MUTLAKA isaretleyin.
  echo.
  pause
  exit /b 1
)

REM 2) Sanal ortam (.venv) olustur
if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo HATA: Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
)

REM 3) Bagimliliklari kur
echo Bagimliliklar kuruluyor (internet gerekir)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo HATA: Bagimliliklar kurulamadi.
  echo   Muhtemel sebep: internet yok veya kurumsal proxy var.
  echo   KURULUM_WINDOWS.md icindeki "Sorun giderme" bolumune bakin.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   KURULUM TAMAM.
echo   Artik calistir.bat ile kullanabilirsiniz.
echo ============================================
pause
