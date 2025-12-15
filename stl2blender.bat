@echo off
cd /d "%~dp0"
if "%~1"=="" (
    echo Usage: Drag and drop a directory ending in __STL onto this script.
    pause
    exit /b
)
uv run python stl2blender.py "%~1"
pause
