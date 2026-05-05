# Netdef GUI Launcher - Full Bidirectional Bridge
# HTML->PS: Command queue polling via InvokeScript('getPendingCommands')
# PS->HTML: Status callbacks via InvokeScript('onCommandResult', json)

param(
    [switch]$Legacy
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$htmlGuiPath = Join-Path $scriptPath "netdef-gui-redesigned.html"
$psGuiPath = Join-Path $scriptPath "netdef-gui.ps1"

# ============================================================
# ALL FUNCTIONS DEFINED FIRST (before event handlers use them)
# ============================================================

function script:SendCommandResult {
    param($Browser, [string]$Action, [bool]$Success, [string]$Message, [hashtable]$Extra)
    if (-not $Browser -or -not $Browser.Document) { return }

    $successStr = $Success.ToString().ToLower()
    $extraStr = ''
    if ($Extra) {
        foreach ($key in $Extra.Keys) {
            if ($key -eq 'profile' -or $key -eq 'running') {
                $extraStr = $Extra[$key].ToString().ToLower()
            }
        }
    }

    Write-Host "[RESULT] action=$Action success=$successStr msg=$Message extra=$extraStr" -ForegroundColor Green

    try {
        $Browser.Document.InvokeScript('onResult', @($Action, $successStr, $Message, $extraStr)) | Out-Null
    } catch {
        Write-Host "[WARN] onResult failed, trying JSON: $_" -ForegroundColor Yellow
        try {
            $resultObj = @{ action = $Action; success = $Success; message = $Message }
            if ($Extra) {
                foreach ($key in $Extra.Keys) { $resultObj[$key] = $Extra[$key] }
            }
            $resultJson = $resultObj | ConvertTo-Json -Compress
            $Browser.Document.InvokeScript('onCommandResult', @($resultJson)) | Out-Null
        } catch {
            Write-Host "[WARN] JSON callback also failed: $_" -ForegroundColor Red
        }
    }
}

function script:ExecuteProfileScript {
    param([string]$Profile, [string]$ScriptDir)
    $batFiles = @{ 'home' = 'lan-config.bat'; 'office' = 'lan-config.bat'; 'travel' = 'outdoor-config.bat'; 'lockdown' = 'lan-config.bat' }
    $profileNames = @{ 'home' = 'Home'; 'office' = 'Office'; 'travel' = 'Travel'; 'lockdown' = 'Lockdown' }
    $batFile = $batFiles[$Profile.ToLower()]
    if (-not $batFile) { return @{ Success = $false; Message = "Unknown profile: $Profile" } }
    $fullPath = Join-Path $ScriptDir $batFile
    if (-not (Test-Path $fullPath)) { return @{ Success = $false; Message = "Script not found: $batFile" } }
    $profileName = $profileNames[$Profile.ToLower()]
    Write-Host "[EXEC] Running: $fullPath (Profile: $profileName)" -ForegroundColor Cyan
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "cmd.exe"
        $psi.Arguments = "/c `"$fullPath`""
        $psi.WorkingDirectory = $ScriptDir
        $psi.UseShellExecute = $true
        $psi.Verb = "runas"
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        return @{ Success = $true; Message = "$profileName profile execution started" }
    } catch {
        return @{ Success = $false; Message = "Start failed: $_" }
    }
}

function script:ToggleWail2Ban {
    param([bool]$Start, [string]$ScriptDir)
    $mgrBat = Join-Path $ScriptDir "wail2ban-manager.bat"
    if (-not (Test-Path $mgrBat)) { return @{ Success = $false; Message = "Wail2Ban manager script not found" } }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "cmd.exe"
        if ($Start) { $psi.Arguments = "/c `"$mgrBat`"" } else { $psi.Arguments = "/c `"$mgrBat`" /stop" }
        $psi.WorkingDirectory = $ScriptDir
        $psi.UseShellExecute = $true
        $psi.Verb = "runas"
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        $label = if ($Start) { 'start' } else { 'stop' }
        return @{ Success = $true; Message = "Wail2Ban ${label} command sent" }
    } catch {
        return @{ Success = $false; Message = "Wail2Ban operation failed: $_" }
    }
}

function script:ExecuteCleanup {
    param([string]$ScriptDir)
    $cleanupBat = Join-Path $ScriptDir "cleanup-rules.bat"
    if (-not (Test-Path $cleanupBat)) { return @{ Success = $false; Message = "Cleanup script not found" } }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "cmd.exe"
        $psi.Arguments = "/c `"$cleanupBat`""
        $psi.WorkingDirectory = $ScriptDir
        $psi.UseShellExecute = $true
        $psi.Verb = "runas"
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        return @{ Success = $true; Message = "Firewall cleanup started" }
    } catch {
        return @{ Success = $false; Message = "Cleanup failed: $_" }
    }
}

function script:OpenConfigFile {
    param([string]$ScriptDir)
    $configFile = Join-Path $ScriptDir "setting.ini"
    if (Test-Path $configFile) {
        Start-Process notepad.exe -ArgumentList "`"$configFile`""
        return @{ Success = $true; Message = "Config file opened" }
    } else {
        return @{ Success = $false; Message = "Config file not found: setting.ini" }
    }
}

function script:OpenLogsFolder {
    param([string]$ScriptDir)
    $logDir = Join-Path $ScriptDir "logs"
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Start-Process explorer.exe -ArgumentList "`"$logDir`""
    return @{ Success = $true; Message = "Logs folder opened" }
}

function script:SyncSystemStatus {
    param($Browser, $ScriptDir)
    try {
        $fwProfiles = Get-NetFirewallProfile -ErrorAction SilentlyContinue
        $allActive = $true
        foreach ($p in $fwProfiles) { if ($p.Enabled -ne $true) { $allActive = $false; break } }
        $fwActive = $allActive
        Write-Host "[SYNC] Firewall: $(if($fwActive){'Active'}else{'Inactive'})" -ForegroundColor Cyan
        if ($Browser.Document) { $Browser.Document.InvokeScript('updateFirewallStatus', @($fwActive.ToString().ToLower())) | Out-Null }
    } catch {
        Write-Host "[SYNC] Firewall check failed: $_" -ForegroundColor Yellow
        if ($Browser.Document) { $Browser.Document.InvokeScript('updateFirewallStatus', @('true')) | Out-Null }
    }
    try {
        $w2bProcs = Get-CimInstance Win32_Process -Filter "name='powershell.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*wail2ban*' }
        $w2bRunning = ($w2bProcs -ne $null -and $w2bProcs.Count -gt 0)
        Write-Host "[SYNC] Wail2Ban: $(if($w2bRunning){'Running'}else{'Stopped'})" -ForegroundColor Cyan
        if ($Browser.Document) { $Browser.Document.InvokeScript('updateWail2BanStatus', @($w2bRunning.ToString().ToLower())) | Out-Null }
    } catch {
        Write-Host "[SYNC] Wail2Ban check failed: $_" -ForegroundColor Yellow
        if ($Browser.Document) { $Browser.Document.InvokeScript('updateWail2BanStatus', @('false')) | Out-Null }
    }
    try {
        $rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like 'Allow ALL from Trusted IPs*' -and $_.Enabled -eq $true }
        $detectedProfile = ''
        if ($rules) {
            $outboundBlock = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like '*Outbound Block*' -and $_.Enabled -eq $true }
            if ($outboundBlock) { $detectedProfile = 'lockdown' } else {
                $portBlockRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like '*Block Outbound*' -and $_.Enabled -eq $true }
                if ($portBlockRules) { $detectedProfile = 'travel' } else { $detectedProfile = 'home' }
            }
        }
        if ($detectedProfile) {
            Write-Host "[SYNC] Detected profile: $detectedProfile" -ForegroundColor Cyan
            if ($Browser.Document) { $Browser.Document.InvokeScript('setCurrentProfile', @($detectedProfile)) | Out-Null }
        }
    } catch {
        Write-Host "[SYNC] Profile detection failed: $_" -ForegroundColor Yellow
    }
    if ($Browser.Document) { $Browser.Document.InvokeScript('pushLog', @('System status sync complete', 'success')) | Out-Null }
}

function script:ProcessCommandFromHtml {
    param([string]$CommandJson, [string]$ScriptDir, $Browser)
    try {
        $commandObj = $CommandJson | ConvertFrom-Json -ErrorAction Stop
        $action = $commandObj.action
        switch ($action.ToLower()) {
            'execute' {
                if ($commandObj.profile) {
                    $result = ExecuteProfileScript -Profile $commandObj.profile -ScriptDir $ScriptDir
                    SendCommandResult -Browser $Browser -Action 'execute' -Success $result.Success -Message $result.Message -Extra @{ profile = $commandObj.profile }
                }
            }
            'wail2ban' {
                $start = $commandObj.start -eq $true -or $commandObj.start -eq 1
                $result = ToggleWail2Ban -Start $start -ScriptDir $ScriptDir
                SendCommandResult -Browser $Browser -Action 'wail2ban' -Success $result.Success -Message $result.Message -Extra @{ running = $start }
            }
            'cleanup' {
                $result = ExecuteCleanup -ScriptDir $ScriptDir
                SendCommandResult -Browser $Browser -Action 'cleanup' -Success $result.Success -Message $result.Message
            }
            'config' {
                $result = OpenConfigFile -ScriptDir $ScriptDir
                SendCommandResult -Browser $Browser -Action 'config' -Success $result.Success -Message $result.Message
            }
            'logs' {
                $result = OpenLogsFolder -ScriptDir $ScriptDir
                SendCommandResult -Browser $Browser -Action 'logs' -Success $result.Success -Message $result.Message
            }
            'refresh' {
                SyncSystemStatus -Browser $Browser -ScriptDir $ScriptDir
                if ($Browser.Document) { $Browser.Document.InvokeScript('pushLog', @('Status refresh complete', 'success')) | Out-Null }
            }
            default { Write-Host "[WARN] Unknown action: $action" -ForegroundColor Yellow }
        }
    } catch {
        Write-Host "[ERROR] Command processing: $_" -ForegroundColor Red
        SendCommandResult -Browser $Browser -Action 'error' -Success $false -Message "Command failed: $_"
    }
}

# ============================================================
# MAIN GUI CODE (uses functions defined above)
# ============================================================

if ((-not $Legacy) -and (Test-Path $htmlGuiPath)) {
    Write-Host "Launching Netdef GUI (Full Bridge Mode)..." -ForegroundColor Cyan

    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing

        $exeName = [System.IO.Path]::GetFileName([System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)
        $ieKeyPath = "HKCU:\Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"
        if (-not (Test-Path $ieKeyPath)) { New-Item -Path $ieKeyPath -Force | Out-Null }
        Set-ItemProperty -Path $ieKeyPath -Name $exeName -Value 11001 -Type DWord -ErrorAction SilentlyContinue
        Write-Host "[OK] IE11 rendering mode enabled" -ForegroundColor Green

        $form = New-Object System.Windows.Forms.Form
        $form.Text = "Netdef Security Suite - Network Definer v1.0"
        $form.Size = New-Object System.Drawing.Size(1170, 770)
        $form.StartPosition = "CenterScreen"
        $form.FormBorderStyle = "FixedDialog"
        $form.MaximizeBox = $false
        $form.BackColor = [System.Drawing.Color]::FromArgb(10, 10, 26)
        $form.Icon = [System.Drawing.SystemIcons]::Shield

        $browser = New-Object System.Windows.Forms.WebBrowser
        $browser.Dock = "Fill"
        $browser.IsWebBrowserContextMenuEnabled = $false
        $browser.WebBrowserShortcutsEnabled = $false
        $browser.ScriptErrorsSuppressed = $true

        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 300

        $timer.Add_Tick({
            if ($browser.ReadyState -ne 'Complete') { return }
            try {
                if ($browser.Document) {
                    $result = $browser.Document.InvokeScript('getPendingCommands')
                    if ($result) {
                        $commandJson = if ($result -is [string]) { $result } else { $result.ToString() }
                        if ($commandJson -and $commandJson.Length -gt 0) {
                            Write-Host "[CMD] $commandJson" -ForegroundColor Yellow
                            ProcessCommandFromHtml -CommandJson $commandJson -ScriptDir $scriptPath -Browser $browser
                        }
                    }
                }
            } catch {
                Write-Host "[ERROR] Polling: $_" -ForegroundColor Red
            }
        })

        $htmlUrl = "file:///" + ($htmlGuiPath -replace '\\', '/')
        $browser.Navigate($htmlUrl)

        $browser.Add_DocumentCompleted({
            param($sender, $e)
            $form.Text = "Netdef Security Suite - Network Definer"
            $timer.Start()
            Write-Host "[OK] GUI loaded. Bridge active." -ForegroundColor Cyan
            try {
                $browser.Document.InvokeScript('setEmbeddedMode') | Out-Null
                Write-Host "[OK] Embedded mode flag set" -ForegroundColor Green
            } catch {
                Write-Host "[WARN] Could not set embedded mode: $_" -ForegroundColor Yellow
            }
            SyncSystemStatus -Browser $browser -ScriptDir $scriptPath
        })

        $form.Controls.Add($browser)
        $form.Add_FormClosing({ $timer.Stop() })
        [void]$form.ShowDialog()
    }
    catch {
        Write-Host "Failed: $_" -ForegroundColor Red
        Start-Process $htmlGuiPath
    }
}
else {
    if (Test-Path $psGuiPath) { & $psGuiPath }
}