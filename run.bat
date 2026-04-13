@echo off
chcp 65001 > nul
echo.
echo  ============================================
echo   ReadAloud — E-Book Reader with Edge TTS
echo  ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.12+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies if needed
echo  Checking dependencies...
pip show flask >nul 2>&1 || pip install -r requirements.txt
pip show edge-tts >nul 2>&1 || pip install -r requirements.txt
pip show deep-translator >nul 2>&1 || pip install -r requirements.txt

echo.
echo  Starting ReadAloud → http://localhost:5000
echo  Press Ctrl+C to stop.
echo.

python app.py
pause
