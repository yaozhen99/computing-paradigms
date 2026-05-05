# watchdog.ps1 — Minimal Watchdog
# Runs every 2 min via Task Scheduler
# 1. read signal_kill -> taskkill -> delete signal
# 2. read signal_start -> launch -> delete signal
# 3. check heartbeat timeout -> wake AI

$SystemDir = "C:\quant_system_v1.1_ths\_system"
$ProjectDir = "C:\quant_system_v1.1_ths"
$TimeoutSec = 600

# 1. signal_kill
Get-ChildItem -Path "$SystemDir\signal_kill_*.json" -ErrorAction SilentlyContinue | ForEach-Object {
    $sig = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $targetPid = $sig.pid
    $useForce = $sig.force -eq $true
    if ($useForce) {
        taskkill /F /T /PID $targetPid 2>$null
    } else {
        taskkill /PID $targetPid 2>$null
    }
    Remove-Item $_.FullName -Force
}

# 2. signal_start — 直接启动，不用 cmd.exe 包装
Get-ChildItem -Path "$SystemDir\signal_start_*.json" -ErrorAction SilentlyContinue | ForEach-Object {
    $sig = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $cmd = $sig.command
    $wd = if ($sig.working_dir) { $sig.working_dir } else { $ProjectDir }
    $tokens = $cmd -split ' ', 2
    $exe = $tokens[0]
    $args = if ($tokens.Length -gt 1) { $tokens[1] } else { "" }
    if ($sig.detached -eq $true) {
        if ($args) {
            Start-Process $exe -ArgumentList $args -WorkingDirectory $wd -WindowStyle Hidden
        } else {
            Start-Process $exe -WorkingDirectory $wd -WindowStyle Hidden
        }
    } else {
        if ($args) {
            Start-Process $exe -ArgumentList $args -WorkingDirectory $wd
        } else {
            Start-Process $exe -WorkingDirectory $wd
        }
    }
    Remove-Item $_.FullName -Force
}

# 3. heartbeat timeout
$stateFile = Join-Path $SystemDir "system_state.json"
if (Test-Path $stateFile) {
    $state = Get-Content $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $last = [DateTime]::Parse($state.last_heartbeat)
    $elapsed = ((Get-Date) - $last).TotalSeconds
    if ($elapsed -gt $TimeoutSec -and $state.status -ne "offline") {
        $wakeScript = Join-Path $ProjectDir "wake_me.py"
        Start-Process python -ArgumentList $wakeScript, "--task", "watchdog-heartbeat-timeout" -WorkingDirectory $ProjectDir -WindowStyle Hidden
    }
}
