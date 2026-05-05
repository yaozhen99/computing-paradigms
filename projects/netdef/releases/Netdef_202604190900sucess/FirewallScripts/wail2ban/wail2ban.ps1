# Wail2Ban - Dynamic Intrusion Detection and Prevention (Polling Version)
# Customized for Netdef Security Suite
# Compatible with Windows 10/11, Windows Server 2019+

# ========== Initialization ==========
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path $scriptPath -Parent
$iniFile = Join-Path $projectRoot "setting.ini"
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "wail2ban.log"
$stateFile = Join-Path $logDir "state.json"

# Create log directory
if (-not (Test-Path $logDir)) {
    try {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    catch {
        Write-Error "Cannot create log directory: $_"
        exit 1
    }
}

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$time [$Level] $Message"
    try {
        $line | Out-File -FilePath $logFile -Append -Encoding utf8 -ErrorAction Stop
    }
    catch {
        Write-Host "Log write failed: $_" -ForegroundColor Red
    }
    Write-Host $line
}

Write-Log "========== Wail2Ban Started ==========" "START"

# ========== Read Configuration File ==========
if (-not (Test-Path $iniFile)) {
    Write-Log "Configuration file not found: $iniFile" "ERROR"
    exit 1
}

Write-Log "Reading configuration: $iniFile" "INFO"
$ini = Get-Content $iniFile -Raw

# Helper function to extract values from INI file (supports loose parsing)
function Get-IniValue($key) {
    $pattern = "(?m)^$key\s*=\s*(.+?)\s*$"
    if ($ini -match $pattern) {
        return $matches[1].Trim()
    }
    return $null
}

# Read TrustedRanges (required field)
$trustedRanges = Get-IniValue "TrustedRanges"
if (-not $trustedRanges) {
    Write-Log "TrustedRanges not found in configuration" "ERROR"
    exit 1
}
$whitelist = $trustedRanges -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
Write-Log "IP whitelist configured: $($whitelist -join ', ')" "INFO"

# Read Wail2Ban parameters (use defaults if missing)
$eventIDsStr = Get-IniValue "EventIDs"
$findTimeStr = Get-IniValue "FindTime"
$maxRetryStr = Get-IniValue "MaxRetry"
$banTimesStr = Get-IniValue "BanTimes"

if (-not $eventIDsStr) { $eventIDsStr = "4625" }
if (-not $findTimeStr) { $findTimeStr = "300" }
if (-not $maxRetryStr) { $maxRetryStr = "5" }
if (-not $banTimesStr) { $banTimesStr = "3600,18000,90000,450000,7776000" }

$eventIDs = $eventIDsStr -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' } | ForEach-Object { [int]$_ }
$findTime = [int]$findTimeStr
$maxRetry = [int]$maxRetryStr
$banTimes = $banTimesStr -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' } | ForEach-Object { [int]$_ }

Write-Log "Wail2Ban config: EventIDs=$($eventIDs -join ','), FindTime=$findTime, MaxRetry=$maxRetry, BanTimes=$($banTimes -join ',')" "INFO"

# Configuration object
$config = @{
    EventIDs  = $eventIDs
    FindTime  = $findTime
    MaxRetry  = $maxRetry
    BanTimes  = $banTimes
    Whitelist = $whitelist
    LogFile   = $logFile
    StateFile = $stateFile
}

# ========== Whitelist Check Function ==========
function Test-Whitelist {
    param([string]$IP)
    
    # Validate IPv4 address format
    if ($IP -notmatch '^\d+\.\d+\.\d+\.\d+$') {
        Write-Log "Invalid IPv4 address format: $IP" "DEBUG"
        return $false
    }
    
    try {
        $ipBytes = [System.Net.IPAddress]::Parse($IP).GetAddressBytes()
        $ipNum = ($ipBytes[0] -shl 24) + ($ipBytes[1] -shl 16) + ($ipBytes[2] -shl 8) + $ipBytes[3]
    }
    catch {
        Write-Log "IP parse failed for $IP : $_" "WARN"
        return $false
    }
    
    foreach ($range in $config.Whitelist) {
        # Single IP address match
        if ($range -match "^\d+\.\d+\.\d+\.\d+$") {
            if ($IP -eq $range) { return $true }
        }
        # IP range match (e.g., 192.168.1.100-192.168.1.200)
        elseif ($range -match "^(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+)$") {
            try {
                $startBytes = [System.Net.IPAddress]::Parse($matches[1]).GetAddressBytes()
                $endBytes   = [System.Net.IPAddress]::Parse($matches[2]).GetAddressBytes()
                $startNum = ($startBytes[0] -shl 24) + ($startBytes[1] -shl 16) + ($startBytes[2] -shl 8) + ($startBytes[3])
                $endNum   = ($endBytes[0]   -shl 24) + ($endBytes[1]   -shl 16) + ($endBytes[2]   -shl 8) + ($endBytes[3])
                
                if ($ipNum -ge $startNum -and $ipNum -le $endNum) { return $true }
            }
            catch {
                Write-Log "Invalid IP range format: $range" "WARN"
            }
        }
        else {
            Write-Log "Whitelist entry '$range' is not a valid IP or range" "WARN"
        }
    }
    return $false
}

# ========== Firewall Rule Management Functions ==========
function Add-BanRule {
    param([string]$IP, [int]$BanTime)
    $ruleName = "Wail2Ban_$IP"
    
    # Check if rule already exists to avoid netsh errors
    netsh advfirewall firewall show rule name="$ruleName" > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "IP $IP is already in ban list, skipping." "WARN"
        return
    }
    
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=block remoteip=$IP | Out-Null
    Write-Log "Banned IP $IP for $BanTime seconds" "ACTION"
}

function Remove-BanRule {
    param([string]$IP)
    $ruleName = "Wail2Ban_$IP"
    netsh advfirewall firewall delete rule name="$ruleName" | Out-Null
    Write-Log "Unbanned IP $IP" "INFO"
}

# ========== State Management ==========
$state = @{}
if (Test-Path $config.StateFile) {
    try {
        $state = Get-Content $config.StateFile -Raw | ConvertFrom-Json -AsHashtable
        Write-Log "State file loaded successfully" "INFO"
    }
    catch {
        Write-Log "State file corrupted, reinitializing..." "WARN"
    }
}

if (-not $state.ContainsKey("FailCounts")) { $state.FailCounts = @{} }
if (-not $state.ContainsKey("BanHistory")) { $state.BanHistory = @{} }

function Save-State {
    $state | ConvertTo-Json -Depth 3 | Out-File $config.StateFile -Encoding utf8
}

# Cleanup old failure records outside the time window
function Cleanup-FailCounts {
    $now = Get-Date
    $expireTime = $now.AddSeconds(-$config.FindTime)
    $toRemove = @()
    
    foreach ($ip in $state.FailCounts.Keys) {
        $state.FailCounts[$ip] = @($state.FailCounts[$ip] | Where-Object { $_ -ge $expireTime })
        if ($state.FailCounts[$ip].Count -eq 0) {
            $toRemove += $ip
        }
    }
    
    foreach ($ip in $toRemove) {
        $state.FailCounts.Remove($ip)
    }
}

# Process individual security event
function Process-Event {
    param($EventRecord)
    
    $time = $EventRecord.TimeCreated
    $ip = $null
    
    # Extract IP from event properties (Event ID 4625 = login failure)
    if ($EventRecord.Id -in $config.EventIDs -and $EventRecord.Properties.Count -gt 18) {
        $ip = $EventRecord.Properties[18].Value
    }
    
    if (-not $ip) { return }
    
    # Skip whitelisted IPs
    if (Test-Whitelist $ip) { return }

    # Check if already banned and still within ban period
    if ($state.BanHistory.ContainsKey($ip)) {
        $banInfo = $state.BanHistory[$ip]
        $unbanTime = [DateTime]$banInfo.UnbanTime
        
        if ((Get-Date) -lt $unbanTime) {
            return  # Still banned, ignore this event
        }
        else {
            # Ban expired, remove from history and unban
            $state.BanHistory.Remove($ip)
            Remove-BanRule $ip
        }
    }

    # Record this failure attempt
    if (-not $state.FailCounts.ContainsKey($ip)) {
        $state.FailCounts[$ip] = @()
    }
    $state.FailCounts[$ip] += $time

    # Count failures within the time window
    $now = Get-Date
    $windowStart = $now.AddSeconds(-$config.FindTime)
    $recentFails = @($state.FailCounts[$ip] | Where-Object { $_ -ge $windowStart })

    # Check if threshold reached
    if ($recentFails.Count -ge $config.MaxRetry) {
        # Determine ban duration based on offense count (escalating)
        $banCount = if ($state.BanHistory.ContainsKey($ip)) { $state.BanHistory[$ip].Count } else { 0 }
        $banIndex = [Math]::Min($banCount, $config.BanTimes.Count - 1)
        $banTime = $config.BanTimes[$banIndex]
        $unbanTime = $now.AddSeconds($banTime)

        # Apply the ban
        Add-BanRule $ip $banTime

        # Record in ban history
        $state.BanHistory[$ip] = @{
            Count     = $banCount + 1
            BanTime   = $banTime
            UnbanTime = $unbanTime.ToString("o")
            LastFail  = $now.ToString("o")
        }
        
        # Clear failure count after successful ban
        $state.FailCounts.Remove($ip)

        # Log to Windows Event Log for visibility
        try {
            Write-EventLog -LogName Application -Source "Wail2Ban" -EntryType Warning -EventId 1001 -Message "Banned IP: $ip for $banTime seconds" -ErrorAction SilentlyContinue
        }
        catch {}
    }
}

# ========== Main Monitoring Loop (Polling Mode) ==========
function Start-Monitoring {
    Write-Log "Starting polling mode (checking every 10 seconds)..." "INFO"
    
    while ($true) {
        try {
            # Calculate time window for event query
            $startTime = (Get-Date).AddSeconds(-$config.FindTime)
            
            # Query Windows Security Event Log
            $filterHash = @{
                LogName   = 'Security'
                StartTime = $startTime
                ID        = $config.EventIDs
            }
            
            $events = Get-WinEvent -FilterHashtable $filterHash -ErrorAction SilentlyContinue
            
            if ($events) {
                foreach ($evt in $events) {
                    Process-Event $evt
                }
            }

            # Cleanup expired failure records
            Cleanup-FailCounts

            # Check for bans that have expired and should be removed
            $now = Get-Date
            $toUnban = @()
            foreach ($ip in $state.BanHistory.Keys) {
                $unbanTime = [DateTime]$state.BanHistory[$ip].UnbanTime
                if ($now -ge $unbanTime) {
                    $toUnban += $ip
                }
            }
            
            # Remove expired bans
            foreach ($ip in $toUnban) {
                Remove-BanRule $ip
                $state.BanHistory.Remove($ip)
            }

            # Persist state to disk
            Save-State
        }
        catch {
            Write-Log "Monitoring error: $_" "ERROR"
        }
        
        # Wait before next poll
        Start-Sleep -Seconds 10
    }
}

# ========== Start Monitoring ==========
Start-Monitoring
