@echo off
cd /d "%~dp0"
if exist "dist\CalendarioFeriasSTMU.exe" (
    start "" "dist\CalendarioFeriasSTMU.exe"
    exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" run.py
    exit /b
)
echo Execute preparar.bat primeiro ou use o executavel na pasta dist.
pause
