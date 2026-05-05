@echo off

:: Netdef Rule Cleanup Utility
cd /d "%~dp0"

:: Check admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ALERT] Administrator privileges required.
    echo         Requesting elevation...
    powershell start -verb runas '%0'
    exit /b
)

:: Run PowerShell cleanup script
powershell -NoProfile -ExecutionPolicy Bypass -File "cleanup-rules.ps1"
