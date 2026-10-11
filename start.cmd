@echo off
cd /d "%~dp0"
if exist "dist\Naiwa.exe" (
    start "" "dist\Naiwa.exe" --panel
    exit /b
)
if not exist ".venv\Scripts\pythonw.exe" (
    python -m venv .venv
    if errorlevel 1 (echo Please install Python 3.10 or newer.& pause& exit /b 1)
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (pause& exit /b 1)
)
start "" ".venv\Scripts\pythonw.exe" "naiwa.py" --panel
