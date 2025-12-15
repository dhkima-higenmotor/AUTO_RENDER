@echo off
cd /d "%~dp0"
if "%~1"=="" (
    echo Usage: 
    echo   1. Drag and Drop an SLDASM file.
    echo   2. Command Line: AUTO_RENDER_TUI.bat file.sldasm --res 1920x1080
    pause
    exit /b
)

uv run python AUTO_RENDER_TUI.py %*
pause
