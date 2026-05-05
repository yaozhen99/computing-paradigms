@echo off
setlocal EnableDelayedExpansion

rem ============================================================
rem OpenClaw Gateway Healthcheck (B2: Config Atomic Write Guard)
rem Validates openclaw.json before gateway launch.
rem If corrupted, restores from .last-good backup.
rem Returns 0 if config is healthy, 1 if recovery was needed.
rem ============================================================

set "OPENCLAW_HOME=%~dp0"
set "OPENCLAW_HOME=%OPENCLAW_HOME:~0,-1%"
set "CONFIG_FILE=%OPENCLAW_HOME%\openclaw.json"
set "LAST_GOOD=%OPENCLAW_HOME%\openclaw.json.last-good"
set "BAK_FILE=%OPENCLAW_HOME%\openclaw.json.bak"
set "SCRIPTS_DIR=%OPENCLAW_HOME%\scripts"
set "LOG_DIR=%OPENCLAW_HOME%\logs"
set "HEALTH_LOG=%LOG_DIR%\gateway-healthcheck.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem --- Step 1: Check config file exists ---
if not exist "%CONFIG_FILE%" (
    call :log "FATAL: openclaw.json not found"
    if exist "%LAST_GOOD%" (
        call :log "Restoring from .last-good"
        copy /y "%LAST_GOOD%" "%CONFIG_FILE%" >nul
        exit /b 1
    )
    if exist "%BAK_FILE%" (
        call :log "Restoring from .bak"
        copy /y "%BAK_FILE%" "%CONFIG_FILE%" >nul
        exit /b 1
    )
    call :log "No backup available. Cannot recover."
    exit /b 1
)

rem --- Step 2: Check config is not empty/truncated ---
for %%f in ("%CONFIG_FILE%") do set "config_size=%%~zf"
if %config_size% lss 64 (
    call :log "Config too small (%config_size% bytes) - likely truncated"
    call :recover
    exit /b 1
)

rem --- Step 3: Validate JSON structure via node script ---
node "%SCRIPTS_DIR%\validate-config.js" "%CONFIG_FILE%" 2>nul
if errorlevel 1 (
    call :log "Config JSON validation failed"
    call :recover
    exit /b 1
)

rem --- Step 4: Update .last-good if config is healthy ---
if not exist "%LAST_GOOD%" (
    copy /y "%CONFIG_FILE%" "%LAST_GOOD%" >nul
    call :log "Created .last-good snapshot"
) else (
    for %%f in ("%CONFIG_FILE%") do set "cfg_time=%%~tf"
    for %%f in ("%LAST_GOOD%") do set "lgood_time=%%~tf"
    if "!cfg_time!" neq "!lgood_time!" (
        copy /y "%CONFIG_FILE%" "%LAST_GOOD%" >nul
        call :log "Updated .last-good snapshot"
    )
)

call :log "Config OK (%config_size% bytes)"
exit /b 0

:recover
    call :log "Attempting recovery..."
    rem Generate ISO timestamp via node script (wmic removed in Win11 24H2+)
    for /f "usebackq" %%t in (`node "%SCRIPTS_DIR%\timestamp.js"`) do set "ts=%%t"
    if exist "%LAST_GOOD%" (
        set "clobbered=%CONFIG_FILE%.clobbered.!ts!Z"
        copy /y "%CONFIG_FILE%" "!clobbered!" >nul 2>&1
        call :log "Saved corrupted config as !clobbered!"
        copy /y "%LAST_GOOD%" "%CONFIG_FILE%" >nul
        call :log "Restored from .last-good"
        exit /b 0
    )
    if exist "%BAK_FILE%" (
        set "clobbered=%CONFIG_FILE%.clobbered.!ts!Z"
        copy /y "%CONFIG_FILE%" "!clobbered!" >nul 2>&1
        call :log "Saved corrupted config as !clobbered!"
        copy /y "%BAK_FILE%" "%CONFIG_FILE%" >nul
        call :log "Restored from .bak"
        exit /b 0
    )
    call :log "No backup available for recovery!"
    exit /b 1

:log
    echo [%DATE% %TIME%] %~1 >> "%HEALTH_LOG%"
    goto :eof
