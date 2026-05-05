@echo off
setlocal EnableDelayedExpansion

rem ============================================================
rem OpenClaw Gateway Watchdog (B1: Crash-Recovery Strategy)
rem Reverses the crash policy: instead of dying silently,
rem the gateway is automatically restarted with backoff.
rem ============================================================

set "OPENCLAW_HOME=%~dp0"
set "OPENCLAW_HOME=%OPENCLAW_HOME:~0,-1%"
set "CONFIG_FILE=%OPENCLAW_HOME%\openclaw.json"
set "LAST_GOOD=%OPENCLAW_HOME%\openclaw.json.last-good"
set "HEALTHCHECK=%OPENCLAW_HOME%\gateway-healthcheck.cmd"
set "GATEWAY_CMD=%OPENCLAW_HOME%\gateway.cmd"
set "LOG_DIR=%OPENCLAW_HOME%\logs"
set "WATCHDOG_LOG=%LOG_DIR%\gateway-watchdog.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem --- Configuration ---
set "MAX_RETRIES=10"
set "BASE_DELAY_SEC=2"
set "MAX_DELAY_SEC=60"
set "RESET_WINDOW_SEC=300"

rem --- State ---
set "retry_count=0"
set "last_crash_epoch=0"

call :log "Watchdog started (pid=%RANDOM%)"

:main_loop
    rem --- B2: Pre-flight config health check ---
    if exist "%HEALTHCHECK%" (
        call "%HEALTHCHECK%"
        if errorlevel 1 (
            call :log "Healthcheck failed - config recovered from last-good"
        )
    )

    rem --- Launch gateway ---
    call :log "Starting gateway (attempt %retry_count%)"
    call "%GATEWAY_CMD%"
    set "exit_code=!ERRORLEVEL!"

    rem --- Normal exit (code 0) - stop watchdog ---
    if %exit_code% equ 0 (
        call :log "Gateway exited normally (code 0). Watchdog stopping."
        goto :eof
    )

    rem --- Intentional restart (code 42) - restart immediately ---
    if %exit_code% equ 42 (
        call :log "Gateway requested restart (code 42). Restarting immediately."
        set "retry_count=0"
        goto :main_loop
    )

    rem --- Crash: apply backoff ---
    call :log "Gateway crashed (code %exit_code%). Applying backoff..."

    rem Calculate current epoch (seconds since midnight)
    for /f "tokens=1-3 delims=:.," %%a in ("%TIME%") do (
        set /a "now_epoch=%%a*3600+1%%b*60+1%%c-100"
    )

    rem Reset retry count if last crash was > RESET_WINDOW_SEC ago
    set /a "elapsed=now_epoch-last_crash_epoch"
    if !elapsed! gtr %RESET_WINDOW_SEC% (
        set "retry_count=0"
    )

    set /a "retry_count+=1"
    set "last_crash_epoch=!now_epoch!"

    rem Cap retries
    if %retry_count% gtr %MAX_RETRIES% (
        call :log "Max retries (%MAX_RETRIES%) exceeded. Giving up."
        exit /b 1
    )

    rem Exponential backoff: BASE * 2^(retry-1), capped at MAX_DELAY
    set /a "delay=%BASE_DELAY_SEC%"
    for /l %%i in (1,1,%retry_count%) do (
        set /a "delay*=2"
        if !delay! gtr %MAX_DELAY_SEC% set "delay=%MAX_DELAY_SEC%"
    )
    call :log "Waiting !delay! seconds before restart..."
    timeout /t !delay! /nobreak >nul
    goto :main_loop

:log
    echo [%DATE% %TIME%] %~1 >> "%WATCHDOG_LOG%"
    echo [%DATE% %TIME%] %~1
    goto :eof
