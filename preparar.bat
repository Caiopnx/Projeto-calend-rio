@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Instalacao concluida. Abra iniciar.bat.
pause
exit /b 0
:error
echo Nao foi possivel preparar. Instale Python 3.12 com Tcl/Tk e pip.
pause
exit /b 1
