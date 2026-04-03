@echo off
:: PomodoroMini - Windows startup registration
:: Run this once as administrator (or normal user is fine for current user startup)

setlocal

:: Get the directory where this bat file lives
set "APP_DIR=%~dp0"
set "SCRIPT=%APP_DIR%pomodoro_mini.py"
set "VBS=%APP_DIR%run_pomodoro.vbs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python from https://python.org
    pause
    exit /b 1
)

:: Create the silent launcher VBS (no console window)
(
echo Set ws = CreateObject^("WScript.Shell"^)
echo ws.Run "pythonw """ ^& "%SCRIPT%" ^& """", 0, False
) > "%VBS%"

:: Copy shortcut to Startup folder
set "LNK=%STARTUP%\PomodoroMini.vbs"
copy /y "%VBS%" "%LNK%" >nul

echo.
echo [OK] PomodoroMini will now start automatically when Windows starts.
echo      Startup file: %LNK%
echo.
echo To remove auto-start, delete: %LNK%
echo.
pause
