@echo off
setlocal enabledelayedexpansion

:: ========== Home Network Security Profile ==========
:: Applies trusted IP whitelist for home/LAN environments

cd /d "%~dp0"

echo =============================================
echo   Netdef: Home Network Security Profile
echo =============================================
echo.

:: ========== Step 1/4: Check Admin Privileges ==========
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ALERT] Administrator privileges required.
    echo         Requesting elevation...
    powershell start -verb runas '%0'
    exit /b
)
echo [OK] Administrator privileges confirmed.

:: ========== Step 2/4: Read Configuration ==========
set "iniFile=%~dp0setting.ini"
if not exist "%iniFile%" (
    echo [ERROR] Configuration file not found: %iniFile%
    pause
    exit /b
)

echo.
echo [INFO] Reading configuration from setting.ini...

:: Read inbound trusted IP ranges (required)
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Inbound]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^TrustedRanges\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "trustedRanges=%%a"
if not defined trustedRanges (
    echo [ERROR] TrustedRanges not found in configuration file.
    pause
    exit /b
)
set "trustedRanges=%trustedRanges: =%"

:: Read Wail2Ban settings (optional)
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Wail2Ban]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^AutoStart\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "w2bAuto=%%a"
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Wail2Ban]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^Path\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "w2bPath=%%a"
if not defined w2bAuto set w2bAuto=1
if not defined w2bPath set "w2bPath=wail2ban\wail2ban.ps1"
set "w2bAuto=%w2bAuto: =%"
set "w2bPath=%w2bPath: =%"

echo [OK] Trusted IP Range(s): %trustedRanges%
echo [OK] Wail2Ban Auto-Start: %w2bAuto%

:: ========== Step 3/4: Generate PowerShell Script ==========
echo.
echo [INFO] Generating security script...
echo.

:: Generate random filename to avoid conflicts
for /f "delims=" %%i in ('powershell -NoProfile -Command "[System.IO.Path]::GetRandomFileName()"') do set "psScript=%temp%\netdef_%%i.ps1"

:: Cleanup any leftover temp scripts from previous runs
for %%f in ("%temp%\netdef_*.ps1") do del "%%f" 2>nul

:: Block 1: Header and default policy
(
echo # Netdef Home Network Profile - Generated Script
echo # Timestamp: %date% %time%
echo Write-Host "[STEP 1/2] Setting default inbound action to BLOCK..." -ForegroundColor Cyan
echo Set-NetFirewallProfile -Name Domain,Private,Public -DefaultInboundAction Block
echo Write-Host "[OK] Default policy applied." -ForegroundColor Green
) > "%psScript%"

:: Block 2: Trust rule creation
(
echo.
echo Write-Host "[STEP 2/2] Creating trust rule for allowed IPs..." -ForegroundColor Cyan
echo $trustedRange = "%trustedRanges%"
echo $ruleName = "Allow ALL from Trusted IPs %trustedRanges%"
echo $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
echo if ^(-not $existingRule^) {
echo     New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -RemoteAddress $trustedRange -Protocol Any
echo     Write-Host "[OK] Rule created: $ruleName" -ForegroundColor Green
echo } else {
echo     Write-Host "[SKIP] Rule already exists: $ruleName" -ForegroundColor Yellow
echo }
) >> "%psScript%"

:: Block 3: Status display
(
echo.
echo Write-Host "" 
echo Write-Host "============================================" -ForegroundColor White
echo Write-Host "  Current Firewall Status:" -ForegroundColor White
echo Write-Host "============================================" -ForegroundColor White
echo Get-NetFirewallProfile ^| Format-Table Name, DefaultInboundAction -AutoSize
echo Write-Host ""
echo Write-Host "Trusted IP Rule Details:" -ForegroundColor Cyan
echo Get-NetFirewallRule -DisplayName $ruleName ^| Format-List
echo Write-Host ""
echo Write-Host "Home Network profile applied successfully!" -ForegroundColor Green
) >> "%psScript%"

:: Verify script was created
if not exist "%psScript%" (
    echo [ERROR] Failed to generate temporary script.
    pause
    exit /b
)

:: ========== Step 4/4: Execute Security Script ==========
echo [INFO] Executing firewall configuration...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%psScript%"
set "execError=%errorlevel%"

:: Cleanup temp script
del "%psScript%" 2>nul

if %execError% neq 0 (
    echo.
    echo [WARN] Script completed with exit code: %execError%
) else (
    echo.
    echo [OK] Home Network configuration completed successfully!
)

:: Enable firewall logging
echo.
echo [INFO] Enabling firewall logging...
netsh advfirewall set allprofiles logging filename "%systemroot%\system32\LogFiles\Firewall\pfirewall.log" >nul
netsh advfirewall set allprofiles logging maxfilesize 4096 >nul
netsh advfirewall set allprofiles logging droppedconnections enable >nul
echo [OK] Firewall drop logging enabled.

:: Optional: Start Wail2Ban if configured
if "%w2bAuto%"=="1" (
    echo.
    echo [INFO] Starting Wail2Ban intrusion detection...
    if exist "%w2bPath%" (
        start /min powershell -NoProfile -ExecutionPolicy Bypass -File "%w2bPath%"
        echo [OK] Wail2Ban started in background.
    ) else (
        echo [WARN] Wail2Ban script not found: %w2bPath%
    )
)

echo.
echo =============================================
echo   Press any key to exit...
echo =============================================
pause >nul
