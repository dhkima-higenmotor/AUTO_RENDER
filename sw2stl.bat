@echo off
cd /d "%~dp0"
if "%~1"=="" (
    echo Usage: Drag and drop an .SLDASM file onto this script.
    pause
    exit /b
)
uv run python sw2stl.py "%~1"
pause
