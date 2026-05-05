@echo off
setlocal enabledelayedexpansion

:: ========== Travel/Public WiFi Security Profile ==========
:: Maximum protection for public networks with port blocking

cd /d "%~dp0"

echo =============================================
echo   Netdef: Travel Mode Security Profile
echo   Public WiFi Maximum Protection
echo =============================================
echo.

:: ========== Step 1/5: Check Admin Privileges ==========
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ALERT] Administrator privileges required.
    echo         Requesting elevation...
    powershell start -verb runas '%0'
    exit /b
)
echo [OK] Administrator privileges confirmed.

:: ========== Step 2/5: Read Configuration ==========
set "iniFile=%~dp0setting.ini"
if not exist "%iniFile%" (
    echo [ERROR] Configuration file not found: %iniFile%
    pause
    exit /b
)

echo.
echo [INFO] Reading configuration from setting.ini...

:: Read inbound trusted ranges (required)
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Inbound]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^TrustedRanges\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "trustedRanges=%%a"
set "trustedRanges=%trustedRanges: =%"
if not defined trustedRanges (
    echo [ERROR] TrustedRanges not found in configuration file.
    pause
    exit /b
)
echo [OK] Trusted IP Range(s): %trustedRanges%

:: Read outbound filtering
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Outbound]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^Enable\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "outboundEnable=%%a"
set "outboundEnable=%outboundEnable: =%"
if not defined outboundEnable set "outboundEnable=0"
echo [OK] Outbound whitelist enabled: %outboundEnable%

:: Read outbound allowed ranges
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Outbound]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^AllowedRanges\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "allowedRanges=%%a"
set "allowedRanges=%allowedRanges: =%"
echo [OK] Outbound allowed range(s): %allowedRanges%

:: Read TCP ports to block
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[OutboundPorts]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^BlockTCP\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "blockTCP=%%a"
set "blockTCP=%blockTCP: =%"
if not defined blockTCP (
    echo [ERROR] BlockTCP not found in configuration file.
    pause
    exit /b
)
echo [OK] Block TCP ports: %blockTCP%

:: Read UDP ports to block
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[OutboundPorts]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^BlockUDP\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "blockUDP=%%a"
set "blockUDP=%blockUDP: =%"
if not defined blockUDP (
    echo [ERROR] BlockUDP not found in configuration file.
    pause
    exit /b
)
echo [OK] Block UDP ports: %blockUDP%

:: Read Wail2Ban settings
for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Wail2Ban]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^AutoStart\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "w2bAuto=%%a"
set "w2bAuto=%w2bAuto: =%"
if not defined w2bAuto set "w2bAuto=0"
echo [OK] Wail2Ban Auto-Start: %w2bAuto%

for /f "delims=" %%a in ('powershell -NoProfile -Command "$ini = Get-Content '%iniFile%' -Raw; $inSection = $false; foreach ($line in $ini -split \"`n\") { $line = $line.Trim(); if ($line -eq '[Wail2Ban]') { $inSection = $true; continue; }; if ($line -match '^\[') { $inSection = $false; continue; }; if ($inSection -and $line -match '^Path\s*=\s*(.+)$') { Write-Output $matches[1].Trim(); break; } }"') do set "w2bPath=%%a"
set "w2bPath=%w2bPath: =%"
if not defined w2bPath set "w2bPath=wail2ban\wail2ban.ps1"
echo [OK] Wail2Ban path: %w2bPath%

echo.
echo [INFO] Applying Travel Mode firewall configuration...
echo.

:: ========== Step 3/5: Execute Security Script ==========
echo [INFO] Executing configuration script...
echo.

:: Set environment variables for PowerShell script
set "trustedRanges=%trustedRanges%"
set "outboundEnable=%outboundEnable%"
set "allowedRanges=%allowedRanges%"
set "blockTCP=%blockTCP%"
set "blockUDP=%blockUDP%"

:: Run PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "outdoor-config.ps1"
set "execError=%errorlevel%"


if %execError% neq 0 (
    echo.
    echo [WARN] Script completed with exit code: %execError%
) else (
    echo.
    echo [OK] Travel Mode configuration completed successfully!
)

:: ========== Step 5/5: Enable Logging ==========
echo.
echo [INFO] Enabling firewall drop logging...
netsh advfirewall set allprofiles logging filename "%systemroot%\system32\LogFiles\Firewall\pfirewall.log" >nul
netsh advfirewall set allprofiles logging maxfilesize 4096 >nul
netsh advfirewall set allprofiles logging droppedconnections enable >nul
echo [OK] Firewall logging enabled.

echo.
echo =============================================
echo   Press any key to exit...
echo =============================================
pause >nul
