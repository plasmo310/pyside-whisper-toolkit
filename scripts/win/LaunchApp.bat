@echo off
REM Whisper Toolkit (GUI) launcher.

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..\..

set PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\pythonw.exe
if not exist "%PYTHON_EXE%" (
    echo Not found python env. Please execute 'scripts\win\setup_venv.bat'.
    pause
    exit /b 1
)

set PYTHONDONTWRITEBYTECODE=1
set PYTHONPATH=%ROOT_DIR%\python

start "" /b "%PYTHON_EXE%" -m wsptoolkit.main
