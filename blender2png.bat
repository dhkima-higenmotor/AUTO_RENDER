@echo off
cd /d "%~dp0"
if "%~1"=="" (
    echo Usage: 
    echo   1. Drag and Drop a .blend file.
    echo   2. CLI: blender2png.bat file.blend --res 1920x1080
    pause
    exit /b
)
uv run python blender2png.py %*
pause
