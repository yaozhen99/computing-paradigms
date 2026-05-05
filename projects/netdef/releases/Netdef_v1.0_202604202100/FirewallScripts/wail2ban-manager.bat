@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "W2B_SCRIPT=wail2ban\wail2ban.ps1"

:: Check admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell start -verb runas '%0' %*
    exit /b
)

if "%1"=="/stop" goto :Stop

:: ========== No Parameters: Start Wail2Ban ==========
echo Starting Wail2Ban intrusion detection...

:: Check if already running - use PowerShell to return exit code
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*wail2ban*' }; if ($p -and $p.Count -gt 0) { exit 1 } else { exit 0 }"
if %errorlevel% equ 1 (
    echo [WARN] Wail2Ban is already running. Only one instance allowed.
    echo        Use "wail2ban-manager.bat /stop" to stop it first.
    pause
    exit /b 1
)

:: Start Wail2Ban in background
start /min powershell -ExecutionPolicy Bypass -File "%W2B_SCRIPT%"
echo [OK] Wail2Ban started successfully.
pause
exit /b 0

:: ========== /stop: Stop Wail2Ban ==========
:Stop
echo Stopping Wail2Ban...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*wail2ban*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo [OK] All Wail2Ban processes terminated.
pause
exit /b 0
