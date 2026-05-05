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

:: Check if already running
powershell -Command "$processes = Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*wail2ban*' }; if ($processes.Count -gt 0) { Write-Host 'Wail2Ban is already running.' -ForegroundColor Yellow; exit }" >nul 2>&1

:: Start Wail2Ban in background
start /min powershell -ExecutionPolicy Bypass -File "%W2B_SCRIPT%"
echo Wail2Ban started successfully.
pause
exit /b

:: ========== /stop: Stop Wail2Ban ==========
:Stop
echo Stopping Wail2Ban...
powershell -Command "Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*wail2ban*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo All Wail2Ban processes terminated.
pause
exit /b
