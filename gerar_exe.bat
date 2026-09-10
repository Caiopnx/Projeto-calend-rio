@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm CalendarioFeriasSTMU.spec
if errorlevel 1 goto error
echo EXE gerado: dist\CalendarioFeriasSTMU.exe
pause
exit /b 0
:error
echo Falha na compilacao. Confira as mensagens acima.
pause
exit /b 1
