# Netdef Travel Mode - Generated Script
param()

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  NETDEF TRAVEL MODE CONFIGURATION" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan

$trustedRange = $env:trustedRanges
$outboundEn = $env:outboundEnable
$allowedRng = $env:allowedRanges
$tcpPorts = $env:blockTCP
$udpPorts = $env:blockUDP

Write-Host "`n[INFO] Loaded configuration:" -ForegroundColor Gray
Write-Host "  Trusted ranges: $trustedRange" -ForegroundColor Cyan
Write-Host "  Outbound filter: $outboundEn" -ForegroundColor Cyan
Write-Host "  Block TCP: $tcpPorts" -ForegroundColor Cyan
Write-Host "  Block UDP: $udpPorts" -ForegroundColor Cyan

# Step 1/4: Configuring inbound trust rules
Write-Host "[STEP 1/4] Configuring inbound trust rules..." -ForegroundColor Cyan
$ranges = $trustedRange -split ','
foreach ($range in $ranges) {
    $range = $range.Trim()
    if ($range) {
        New-NetFirewallRule -DisplayName "Allow Trusted Inbound" -Direction Inbound -Action Allow -RemoteAddress $range -Protocol Any -ErrorAction SilentlyContinue | Out-Null
    }
}
Write-Host "[OK] Inbound rules applied." -ForegroundColor Green

# Step 2/4: Configuring outbound filtering
Write-Host "[STEP 2/4] Configuring outbound filtering..." -ForegroundColor Cyan
if ($outboundEn -eq "1") {
    Set-NetFirewallProfile -DefaultOutboundAction Block
    if ($allowedRng) {
        $outRngs = $allowedRng -split ','
        foreach ($r in $outRngs) {
            $r = $r.Trim()
            if ($r) { New-NetFirewallRule -DisplayName "Allow Outbound" -Direction Outbound -Action Allow -RemoteAddress $r -Protocol Any -ErrorAction SilentlyContinue | Out-Null }
        }
        Write-Host "[OK] Outbound whitelist active." -ForegroundColor Green
    } else {
        Write-Host "[WARN] No allowed ranges specified!" -ForegroundColor Yellow
    }
} else {
    Set-NetFirewallProfile -DefaultOutboundAction Allow
    Write-Host "[INFO] Outbound filtering disabled." -ForegroundColor Gray
}

# Step 3/4: Blocking dangerous ports
Write-Host "[STEP 3/4] Blocking dangerous ports..." -ForegroundColor Cyan
if ($tcpPorts) {
    foreach ($p in ($tcpPorts -split ',')) {
        $p = $p.Trim()
        if ($p) { New-NetFirewallRule -DisplayName "Block TCP $p" -Direction Outbound -Action Block -Protocol TCP -LocalPort $p -ErrorAction SilentlyContinue | Out-Null }
    }
}
if ($udpPorts) {
    foreach ($p in ($udpPorts -split ',')) {
        $p = $p.Trim()
        if ($p) { New-NetFirewallRule -DisplayName "Block UDP $p" -Direction Outbound -Action Block -Protocol UDP -LocalPort $p -ErrorAction SilentlyContinue | Out-Null }
    }
}
Write-Host "[OK] Port blocking rules applied." -ForegroundColor Green

# Step 4/4: Configuration complete
Write-Host "[STEP 4/4] Configuration complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
Get-NetFirewallRule -DisplayName "Allow *", "Block *" -ErrorAction SilentlyContinue | Format-Table DisplayName, Direction, Action -AutoSize
