@echo off
rem ============================================================
rem B1+B2补丁恢复脚本
rem 用途：OpenClaw升级后如果丢失补丁文件，用此脚本一键恢复
rem 备份位置：C:\tower-of-babel\atlas\patch-backup\B1B2\
rem ============================================================

set "BACKUP=C:\tower-of-babel\atlas\patch-backup\B1B2"
set "TARGET=C:\Users\yz01\.openclaw"

echo === B1+B2 Patch Restore ===
echo.

rem --- 恢复watchdog ---
if not exist "%TARGET%\gateway-watchdog.cmd" (
    echo Restoring gateway-watchdog.cmd
    copy /y "%BACKUP%\gateway-watchdog.cmd" "%TARGET%\" >nul
) else (
    echo gateway-watchdog.cmd already exists
)

rem --- 恢复healthcheck ---
if not exist "%TARGET%\gateway-healthcheck.cmd" (
    echo Restoring gateway-healthcheck.cmd
    copy /y "%BACKUP%\gateway-healthcheck.cmd" "%TARGET%\" >nul
) else (
    echo gateway-healthcheck.cmd already exists
)

rem --- 恢复scripts ---
if not exist "%TARGET%\scripts" mkdir "%TARGET%\scripts"
if not exist "%TARGET%\scripts\validate-config.js" (
    echo Restoring validate-config.js
    copy /y "%BACKUP%\scripts\validate-config.js" "%TARGET%\scripts\" >nul
) else (
    echo validate-config.js already exists
)
if not exist "%TARGET%\scripts\timestamp.js" (
    echo Restoring timestamp.js
    copy /y "%BACKUP%\scripts\timestamp.js" "%TARGET%\scripts\" >nul
) else (
    echo timestamp.js already exists
)

rem --- 恢复文档 ---
if not exist "%TARGET%\docs" mkdir "%TARGET%\docs"
if not exist "%TARGET%\docs\patch-B1B2-gateway-resilience.md" (
    echo Restoring patch doc
    copy /y "%BACKUP%\patch-B1B2-gateway-resilience.md" "%TARGET%\docs\" >nul
) else (
    echo patch doc already exists
)

echo.
echo === Re-registering Windows scheduled tasks ===
schtasks /Create /TN "OpenClaw Gateway" /TR "%TARGET%\gateway-watchdog.cmd" /SC ONLOGON /RL HIGHEST /F
schtasks /Create /TN "OpenClaw Gateway (Startup)" /TR "%TARGET%\gateway-watchdog.cmd" /SC ONSTART /DELAY 0000:30 /RL HIGHEST /F

echo.
echo === Done ===
echo If any file was overwritten by upgrade, run this script again with /FORCE:
echo   restore-B1B2-patch.cmd /FORCE
pause
