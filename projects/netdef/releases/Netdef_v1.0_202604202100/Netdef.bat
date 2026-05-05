@echo off
setlocal enabledelayedexpansion

:: ========== Set Console Colors ==========
title Netdef Security Suite - Network Definer
color 0F

:: ========== Get Script Directory ==========
set "TOOL_DIR=%~dp0FirewallScripts"
if not exist "%TOOL_DIR%" (
    echo ERROR: FirewallScripts directory not found. Please ensure scripts are in correct location.
    pause
    exit /b 1
)

:: ========== Check Admin Privileges ==========
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell start -verb runas '%0' %*
    exit /b
)

:: ========== If Parameters Provided, Execute Directly ==========
if not "%~1"=="" (
    call :ExecuteParam %*
    exit /b
)

:: ========== No Parameters: Show Interactive Menu ==========
:Menu
cls
echo ========================================
echo        Netdef Security Suite
echo        (Network Definer)
echo ========================================
echo.
echo   [1] Home Network (LAN Config)
echo   [2] Travel Mode (Public WiFi)
echo   [3] Clean Up Rules
echo   [4] Start Wail2Ban Guardian
echo   [5] Stop Wail2Ban Guardian
echo   [6] Full Exit (Clean Rules + Stop Guardian)
echo   [7] Log Viewer
echo   [8] Launch Animated GUI
echo   [0] Exit
echo.
set /p choice="Please select an option (0-8): "

if "%choice%"=="0" exit /b
if "%choice%"=="1" call :ExecuteParam 1 & goto :Menu
if "%choice%"=="2" call :ExecuteParam 2 & goto :Menu
if "%choice%"=="3" call :ExecuteParam 3 & goto :Menu
if "%choice%"=="4" call :ExecuteParam 4 & goto :Menu
if "%choice%"=="5" call :ExecuteParam 5 & goto :Menu
if "%choice%"=="6" call :ExecuteParam 6 & goto :Menu
if "%choice%"=="7" goto :LogSubMenu
if "%choice%"=="8" start powershell -ExecutionPolicy Bypass -File "%TOOL_DIR%\netdef-gui-launcher.ps1" & goto :Menu
goto :Menu

:: ========== Log Submenu ==========
:LogSubMenu
cls
echo ======== Log Viewer ========
echo.
echo   Logs are stored in: %TOOL_DIR%\logs\
echo.
echo   [1] View Wail2Ban Log
echo   [2] View Firewall Log
echo   [3] Open Log Folder in Explorer
echo   [4] Clear All Logs
echo   [0] Back to Main Menu
echo.
set /p logChoice="Please select: "

if "%logChoice%"=="0" goto :Menu
if "%logChoice%"=="1" goto :ViewWail2BanLog
if "%logChoice%"=="2" goto :ViewFirewallLog
if "%logChoice%"=="3" explorer "%TOOL_DIR%\logs" & goto :LogSubMenu
if "%logChoice%"=="4" goto :CleanLogs
goto :LogSubMenu

:ViewWail2BanLog
set "lines=50"
set /p lines="Enter number of lines to view (default 50): "
if "!lines!"=="" set "lines=50"
if exist "%TOOL_DIR%\logs\wail2ban.log" (
    echo.
    echo === Wail2Ban Log (last %lines% lines) ===
    powershell -Command "Get-Content '%TOOL_DIR%\logs\wail2ban.log' -Tail !lines!"
) else (
    echo.
    echo Wail2Ban log file not found at: %TOOL_DIR%\logs\wail2ban.log
    echo Run Wail2Ban first to generate logs.
)
pause
goto :LogSubMenu

:ViewFirewallLog
set "lines=50"
set /p lines="Enter number of lines to view (default 50): "
if "!lines!"=="" set "lines=50"
if exist "%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log" (
    echo.
    echo === Windows Firewall Log (last %lines% lines) ===
    powershell -Command "Get-Content '%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log' -Tail !lines!"
) else (
    echo.
    echo Windows Firewall log not enabled or file missing.
)
pause
goto :LogSubMenu

:CleanLogs
echo.
echo This will clear:
echo   - Wail2Ban log: %TOOL_DIR%\logs\wail2ban.log
echo   - State file: %TOOL_DIR%\logs\state.json
echo   - Windows Firewall drop log
echo.
set /p confirm="Are you sure? (Y/N): "
if /i "%confirm%"=="Y" (
    if exist "%TOOL_DIR%\logs\wail2ban.log" del /q "%TOOL_DIR%\logs\wail2ban.log" && echo Cleared Wail2Ban log.
    if exist "%TOOL_DIR%\logs\state.json" del /q "%TOOL_DIR%\logs\state.json" && echo Cleared state file.
    if exist "%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log" del /q "%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log" && echo Cleared firewall log.
    echo.
    echo All logs cleared successfully.
) else (
    echo Operation cancelled.
)
pause
goto :LogSubMenu

:: ========== Parameter Execution Engine ==========
:ExecuteParam
cd /d "%TOOL_DIR%" || (
    echo [ERROR] Cannot access FirewallScripts directory
    pause
    exit /b 1
)

if "%1"=="1" (
    start lan-config.bat
    exit /b
)
if "%1"=="2" (
    start outdoor-config.bat
    exit /b
)
if "%1"=="3" (
    start cleanup-rules.bat
    exit /b
)
if "%1"=="4" (
    start wail2ban-manager.bat
    exit /b
)
if "%1"=="5" (
    start wail2ban-manager.bat /stop
    exit /b
)
if "%1"=="6" (
    start cleanup-rules.bat
    start wail2ban-manager.bat /stop
    exit /b
)
if "%1"=="7" goto :LogSubMenu
exit /b
