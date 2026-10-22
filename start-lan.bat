@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 start_lan.py %*
    pause
    exit /b
)
where python >nul 2>nul
if %errorlevel% equ 0 (
    python start_lan.py %*
    pause
    exit /b
)
echo Python 3.11+ is required. Install Python, then run this file again.
pause
