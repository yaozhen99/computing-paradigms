# Netdef GUI - Network Definer Security Suite
# Simple yet powerful graphical interface for Netdef
# Built with Windows Forms (PowerShell)
# Compatible with Windows 10/11, Server 2019+

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ========== Global Variables ==========
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path $scriptPath -Parent
$configFile = Join-Path $projectRoot "setting.ini"
$logsDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logsDir "wail2ban.log"

# ========== Helper Functions ==========
function Write-StatusLog {
    param([string]$Message, [Control]$TextBox)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $TextBox.AppendText("[$timestamp] $Message`r`n")
    $TextBox.ScrollToCaret()
}

function Test-AdminPrivileges {
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch {
        return $false
    }
}

function Get-FirewallStatus {
    try {
        $profiles = Get-NetFirewallProfile -ErrorAction SilentlyContinue
        $rules = Get-NetFirewallRule -DisplayName "Allow*" -ErrorAction SilentlyContinue
        
        $status = @{
            Profiles = $profiles | ForEach-Object { "$($_.Name): Inbound=$($_.DefaultInboundAction)" }
            TrustedRules = ($rules | Where-Object { $_.Direction -eq 'Inbound' }).Count
            OutboundRules = ($rules | Where-Object { $_.Direction -eq 'Outbound' }).Count
        }
        return $status
    }
    catch {
        return @{Profiles = @("Error retrieving status"); TrustedRules = 0; OutboundRules = 0 }
    }
}

function Get-Wail2BanStatus {
    if (Test-Path $logFile) {
        try {
            $content = Get-Content $logFile -Tail 20
            $lastLine = $content[-1]
            
            # Check if process is running
            $processRunning = Get-CimInstance Win32_Process -Filter "name='powershell.exe'" -ErrorAction SilentlyContinue | 
                              Where-Object { $_.CommandLine -like '*wail2ban*' }
            
            return @{
                Running = ($processRunning.Count -gt 0)
                LastActivity = $lastLine
                LogExists = $true
            }
        }
        catch {
            return @{Running = $false; LastActivity = "Error reading log"; LogExists = $true}
        }
    }
    else {
        return @{Running = $false; LastActivity = "Not started yet"; LogExists = $false}
    }
}

function Invoke-SecurityProfile {
    param([string]$Profile, [string]$Script)
    
    # Check admin
    if (-not (Test-AdminPrivileges)) {
        [System.Windows.Forms.MessageBox]::Show(
            "Administrator privileges required.`n`nThe script will prompt for elevation.",
            "Privilege Required",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
    }
    
    Write-StatusLog "Applying profile: $Profile" $txtStatus
    
    try {
        Start-Process -FilePath "$scriptPath\$Script" -WorkingDirectory $scriptPath -Verb RunAs -Wait
        Write-StatusLog "Profile '$Profile' applied successfully!" $txtStatus
        Refresh-Status
    }
    catch {
        Write-StatusLog "ERROR: Failed to apply profile: $_" $txtStatus
    }
}

function Open-LogFile {
    if (Test-Path $logsDir) {
        Start-Process explorer.exe $logsDir
    }
    else {
        [System.Windows.Forms.MessageBox]::Show(
            "Log directory does not exist yet.`nRun Wail2Ban first to generate logs.",
            "No Logs",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
    }
}

function Edit-ConfigFile {
    if (Test-Path $configFile) {
        Start-Process notepad.exe $configFile
    }
    else {
        [System.Windows.Forms.MessageBox]::Show(
            "Configuration file not found:`n$configFile",
            "File Not Found",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
    }
}

function Refresh-Status {
    # Update firewall status
    $fwStatus = Get-FirewallStatus
    $lblFWStatus.Text = "Active Rules: $($fwStatus.TrustedRules) inbound, $($fwStatus.OutboundRules) outbound"
    
    # Update Wail2Ban status
    $w2bStatus = Get-Wail2BanStatus
    if ($w2bStatus.Running) {
        $lblW2BStatus.Text = "✅ RUNNING"
        $lblW2BStatus.ForeColor = [System.Drawing.Color]::Green
    }
    else {
        $lblW2BStatus.Text = "⏹ STOPPED"
        $lblW2BStatus.ForeColor = [System.Drawing.Color]::Red
    }
    
    # Update log path display
    $lnkLogs.Text = "📁 Logs: $logsDir"
    
    Write-StatusLog "Status refreshed at $(Get-Date -Format 'HH:mm:ss')" $txtStatus
}

# ========== Create Main Form ==========
$form = New-Object System.Windows.Forms.Form
$form.Text = "🛡️ Netdef Security Suite - Network Definer v1.0"
$form.Size = New-Object System.Drawing.Size(620, 580)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$form.BackColor = [System.Drawing.Color]::FromArgb(240, 248, 255)  # AliceBlue background

# ========== Title Label ==========
$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "Network Definer - Personal Security Suite"
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 102, 204)  # Blue
$lblTitle.Location = New-Object System.Drawing.Point(20, 15)
$lblTitle.Size = New-Object System.Drawing.Size(560, 30)
$lblTitle.TextAlign = "MiddleCenter"
$form.Controls.Add($lblTitle)

# Subtitle
$lblSubtitle = New-Object System.Windows.Forms.Label
$lblSubtitle.Text = "Built with ❤️ and TRAE SOLO AI | Zero Trust Security Made Simple"
$lblSubtitle.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$lblSubtitle.ForeColor = [System.Drawing.Color]::Gray
$lblSubtitle.Location = New-Object System.Drawing.Point(20, 45)
$lblSubtitle.Size = New-Object System.Drawing.Size(560, 20)
$lblSubtitle.TextAlign = "MiddleCenter"
$form.Controls.Add($lblSubtitle)

# Separator line 1
$sep1 = New-Object System.Windows.Forms.Label
$sep1.Text = "─" * 70
$sep1.Location = New-Object System.Drawing.Point(10, 70)
$sep1.Size = New-Object System.Drawing.Size(590, 15)
$sep1.ForeColor = [System.Drawing.Color]::LightGray
$form.Controls.Add($sep1)

# ========== Profile Buttons Section ==========
$lblProfiles = New-Object System.Windows.Forms.Label
$lblProfiles.Text = "🎯 Security Profiles (Select Your Location):"
$lblProfiles.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$lblProfiles.Location = New-Object System.Drawing.Point(20, 90)
$lblProfiles.Size = New-Object System.Drawing.Size(400, 25)
$form.Controls.Add($lblProfiles)

# Button dimensions
$btnWidth = 270
$btnHeight = 60
$btnXStart = 20
$btnYStart = 120
$btnSpacing = 10

# Home Button
$btnHome = New-Object System.Windows.Forms.Button
$btnHome.Text = "🏠 HOME NETWORK`nTrusted LAN Environment`nStandard Security"
$btnHome.Location = New-Object System.Drawing.Point($btnXStart, $btnYStart)
$btnHome.Size = New-Object System.Drawing.Size($btnWidth, $btnHeight)
$btnHome.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnHome.BackColor = [System.Drawing.Color]::FromArgb(144, 238, 144)  # LightGreen
$btnHome.FlatStyle = "Flat"
$btnHome.FlatAppearance.BorderColor = [System.Drawing.Color]::DarkGreen
$btnHome.Cursor = "Hand"
$btnHome.Add_Click({ Invoke-SecurityProfile -Profile "Home Network" -Script "lan-config.bat" })
$form.Controls.Add($btnHome)

# Office Button
$btnOffice = New-Object System.Windows.Forms.Button
$btnOffice.Text = "💼 OFFICE MODE`nCorporate Network`nBalanced Security"
$btnOffice.Location = New-Object System.Drawing.Point($btnXStart + $btnWidth + $btnSpacing, $btnYStart)
$btnOffice.Size = New-Object System.Drawing.Size($btnWidth, $btnHeight)
$btnOffice.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnOffice.BackColor = [System.Drawing.Color]::FromArgb(173, 216, 230)  # LightBlue
$btnOffice.FlatStyle = "Flat"
$btnOffice.FlatAppearance.BorderColor = [System.Drawing.Color]::DarkBlue
$btnOffice.Cursor = "Hand"
$btnOffice.Add_Click({ Invoke-SecurityProfile -Profile "Office Mode" -Script "lan-config.bat" })
$form.Controls.Add($btnOffice)

# Travel Button (Highlighted!)
$btnTravel = New-Object System.Windows.Forms.Button
$btnTravel.Text = "✈️ TRAVEL MODE ⭐`nPublic WiFi Protection`nHIGH Security"
$btnTravel.Location = New-Object System.Drawing.Point($btnXStart, $btnYStart + $btnHeight + $btnSpacing)
$btnTravel.Size = New-Object System.Drawing.Size($btnWidth, $btnHeight)
$btnTravel.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$btnTravel.BackColor = [System.Drawing.Color]::FromArgb(255, 182, 193)  # LightPink
$btnTravel.FlatStyle = "Flat"
$btnTravel.FlatAppearance.BorderColor = [System.Drawing.Color]::DeepPink
$btnTravel.Cursor = "Hand"
$btnTravel.Add_Click({ Invoke-SecurityProfile -Profile "Travel Mode" -Script "outdoor-config.bat" })
$form.Controls.Add($btnTravel)

# Lockdown Button
$btnLockdown = New-Object System.Windows.Forms.Button
$btnLockdown.Text = "🔒 LOCKDOWN MODE`nMaximum Isolation`nPARANOID Security"
$btnLockdown.Location = New-Object System.Drawing.Point($btnXStart + $btnWidth + $btnSpacing, $btnYStart + $btnHeight + $btnSpacing)
$btnLockdown.Size = New-Object System.Drawing.Size($btnWidth, $btnHeight)
$btnLockdown.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnLockdown.BackColor = [System.Drawing.Color]::FromArgb(211, 211, 211)  # LightGray
$btnLockdown.FlatStyle = "Flat"
$btnLockdown.FlatAppearance.BorderColor = [System.Drawing.Color]::Black
$btnLockdown.Cursor = "Hand"
$btnLockdown.Add_Click({
    $result = [System.Windows.Forms.MessageBox]::Show(
        "Lockdown Mode will block ALL outbound traffic except explicitly allowed.`n`nThis may break internet connectivity!`n`nAre you sure?",
        "Confirm Lockdown",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
        Invoke-SecurityProfile -Profile "Lockdown Mode" -Script "outdoor-config.bat"
    }
})
$form.Controls.Add($btnLockdown)

# Separator line 2
$sep2 = New-Object System.Windows.Forms.Label
$sep2.Text = "─" * 70
$sep2.Location = New-Object System.Drawing.Point(10, 265)
$sep2.Size = New-Object System.Drawing.Size(590, 15)
$sep2.ForeColor = [System.Drawing.Color]::LightGray
$form.Controls.Add($sep2)

# ========== Status Panel ==========
$lblStatusTitle = New-Object System.Windows.Forms.Label
$lblStatusTitle.Text = "📊 Current Status:"
$lblStatusTitle.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$lblStatusTitle.Location = New-Object System.Drawing.Point(20, 280)
$lblStatusTitle.Size = New-Object System.Drawing.Size(200, 25)
$form.Controls.Add($lblStatusTitle)

# Firewall Status
$lblFWLabel = New-Object System.Windows.Forms.Label
$lblFWLabel.Text = "Firewall:"
$lblFWLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$lblFWLabel.Location = New-Object System.Drawing.Point(20, 305)
$lblFWLabel.Size = New-Object System.Drawing.Size(80, 20)
$form.Controls.Add($lblFWLabel)

$lblFWStatus = New-Object System.Windows.Forms.Label
$lblFWStatus.Text = "Loading..."
$lblFWStatus.Location = New-Object System.Drawing.Point(100, 305)
$lblFWStatus.Size = New-Object System.Drawing.Size(480, 20)
$lblFWStatus.ForeColor = [System.Drawing.Color]::DarkBlue
$form.Controls.Add($lblFWStatus)

# Wail2Ban Status
$lblW2BLabel = New-Object System.Windows.Forms.Label
$lblW2BLabel.Text = "Wail2Ban:"
$lblW2BLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$lblW2BLabel.Location = New-Object System.Drawing.Point(20, 328)
$lblW2BLabel.Size = New-Object System.Drawing.Size(80, 20)
$form.Controls.Add($lblW2BLabel)

$lblW2BStatus = New-Object System.Windows.Forms.Label
$lblW2BStatus.Text = "Checking..."
$lblW2BStatus.Location = New-Object System.Drawing.Point(100, 328)
$lblW2BStatus.Size = New-Object System.Drawing.Size(150, 20)
$lblW2BStatus.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($lblW2BStatus)

# Log file link
$lnkLogs = New-Object System.Windows.Forms.LinkLabel
$lnkLogs.Text = "📁 Click to open log folder"
$lnkLogs.Location = New-Object System.Drawing.Point(260, 328)
$lnkLogs.Size = New-Object System.Drawing.Size(320, 20)
$lnkLogs.LinkColor = [System.Drawing.Color]::Blue
$lnkLogs.ActiveLinkColor = [System.Drawing.Color]::Red
$lnkLogs.Add_Click({ Open-LogFile })
$form.Controls.Add($lnkLogs)

# Separator line 3
$sep3 = New-Object System.Windows.Forms.Label
$sep3.Text = "─" * 70
$sep3.Location = New-Object System.Drawing.Point(10, 355)
$sep3.Size = New-Object System.Drawing.Size(590, 15)
$sep3.ForeColor = [System.Drawing.Color]::LightGray
$form.Controls.Add($sep3)

# ========== Action Buttons Section ==========
$lblActions = New-Object System.Windows.Forms.Label
$lblActions.Text = "🔧 Quick Actions:"
$lblActions.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$lblActions.Location = New-Object System.Drawing.Point(20, 370)
$lblActions.Size = New-Object System.Drawing.Size(200, 25)
$form.Controls.Add($lblActions)

# Small button dimensions
$sBtnWidth = 130
$sBtnHeight = 35
$sBtnY = 398
$sBtnSpacing = 8

# Start Wail2Ban Button
$btnStartW2B = New-Object System.Windows.Forms.Button
$btnStartW2B.Text = "▶ Start Wail2Ban"
$btnStartW2B.Location = New-Object System.Drawing.Point(20, $sBtnY)
$btnStartW2B.Size = New-Object System.Drawing.Size($sBtnWidth, $sBtnHeight)
$btnStartW2B.BackColor = [System.Drawing.Color]::FromArgb(144, 238, 144)
$btnStartW2B.FlatStyle = "Flat"
$btnStartW2B.Cursor = "Hand"
$btnStartW2B.Add_Click({
    Start-Process -FilePath "wail2ban-manager.bat" -WorkingDirectory $scriptPath -Verb RunAs -Wait
    Write-StatusLog "Wail2Ban started/stopped" $txtStatus
    Refresh-Status
})
$form.Controls.Add($btnStartW2B)

# Clean Up Button
$btnCleanup = New-Object System.Windows.Forms.Button
$btnCleanup.Text = "🧹 Clean Up Rules"
$btnCleanup.Location = New-Object System.Drawing.Point(20 + $sBtnWidth + $sBtnSpacing, $sBtnY)
$btnCleanup.Size = New-Object System.Drawing.Size($sBtnWidth, $sBtnHeight)
$btnCleanup.BackColor = [System.Drawing.Color]::FromArgb(255, 220, 180)  # LightOrange
$btnCleanup.FlatStyle = "Flat"
$btnCleanup.Cursor = "Hand"
$btnCleanup.Add_Click({
    $result = [System.Windows.Forms.MessageBox]::Show(
        "This will remove ALL custom firewall rules.`n`nContinue?",
        "Confirm Cleanup",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    if ($result -eq "Yes") {
        Start-Process -FilePath "cleanup-rules.bat" -WorkingDirectory $scriptPath -Verb RunAs -Wait
        Write-StatusLog "All custom rules cleaned up" $txtStatus
        Refresh-Status
    }
})
$form.Controls.Add($btnCleanup)

# Edit Config Button
$btnEditConfig = New-Object System.Windows.Forms.Button
$btnEditConfig.Text = "⚙️ Edit Config"
$btnEditConfig.Location = New-Object System.Drawing.Point(20 + ($sBtnWidth + $sBtnSpacing) * 2, $sBtnY)
$btnEditConfig.Size = New-Object System.Drawing.Size($sBtnWidth, $sBtnHeight)
$btnEditConfig.BackColor = [System.Drawing.Color]::FromArgb(230, 230, 250)  # Lavender
$btnEditConfig.FlatStyle = "Flat"
$btnEditConfig.Cursor = "Hand"
$btnEditConfig.Add_Click({ Edit-ConfigFile })
$form.Controls.Add($btnEditConfig)

# Refresh Button
$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "🔄 Refresh Status"
$btnRefresh.Location = New-Object System.Drawing.Point(20 + ($sBtnWidth + $sBtnSpacing) * 3, $sBtnY)
$btnRefresh.Size = New-Object System.Drawing.Size($sBtnWidth, $sBtnHeight)
$btnRefresh.BackColor = [System.Drawing.Color]::FromArgb(220, 220, 220)
$btnRefresh.FlatStyle = "Flat"
$btnRefresh.Cursor = "Hand"
$btnRefresh.Add_Click({ Refresh-Status })
$form.Controls.Add($btnRefresh)

# Separator line 4
$sep4 = New-Object System.Windows.Forms.Label
$sep4.Text = "─" * 70
$sep4.Location = New-Object System.Drawing.Point(10, 445)
$sep4.Size = New-Object System.Drawing.Size(590, 15)
$sep4.ForeColor = [System.Drawing.Color]::LightGray
$form.Controls.Add($sep4)

# ========== Activity Log ==========
$lblLogTitle = New-Object System.Windows.Forms.Label
$lblLogTitle.Text = "📝 Activity Log:"
$lblLogTitle.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$lblLogTitle.Location = New-Object System.Drawing.Point(20, 460)
$lblLogTitle.Size = New-Object System.Drawing.Size(100, 20)
$form.Controls.Add($lblLogTitle)

$txtStatus = New-Object System.Windows.Forms.TextBox
$txtStatus.Multiline = $true
$txtStatus.ScrollBars = "Vertical"
$txtStatus.ReadOnly = $true
$txtStatus.BackColor = [System.Drawing.Color]::White
$txtStatus.Font = New-Object System.Drawing.Font("Consolas", 8)
$txtStatus.Location = New-Object System.Drawing.Point(20, 480)
$txtStatus.Size = New-Object System.Drawing.Size(565, 60)
$txtStatus.Text = "Netdef GUI initialized. Select a security profile above to begin...`r`n"
$form.Controls.Add($txtStatus)

# ========== Footer Info ==========
$lblFooter = New-Object System.Windows.Forms.Label
$lblFooter.Text = "💡 Tip: Use Travel Mode on public WiFi for maximum protection | Logs saved locally in FirewallScripts\logs\"
$lblFooter.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$lblFooter.ForeColor = [System.Drawing.Color]::DarkGray
$lblFooter.Location = New-Object System.Drawing.Point(10, 545)
$lblFooter.Size = New-Object System.Drawing.Size(585, 20)
$form.Controls.Add($lblFooter)

# ========== Form Load Event ==========
$form.Add_Load({
    Write-StatusLog "Netdef Security Suite started." $txtStatus
    Write-StatusLog "Version: 1.0.0 | Built with TRAE SOLO AI" $txtStatus
    Refresh-Status
})

# ========== Show Form ==========
[void]$form.ShowDialog()
