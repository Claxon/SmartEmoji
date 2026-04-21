@echo off
setlocal
cd /d "%~dp0"

rem Prefer local .venv; fall back to sibling SmartClipboard venv (same deps).
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%~dp0..\SmartClipboard\.venv\Scripts\pythonw.exe"

if not exist "%PYW%" (
    echo Creating virtualenv...
    py -3 -m venv .venv || goto :fail
    call ".venv\Scripts\activate.bat"
    pip install -r requirements.txt || goto :fail
    set "PYW=%~dp0.venv\Scripts\pythonw.exe"
)

start "" "%PYW%" "%~dp0main.py"
exit /b 0
:fail
echo Setup failed.
pause
exit /b 1
