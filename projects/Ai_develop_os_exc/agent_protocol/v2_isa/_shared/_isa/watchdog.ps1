# watchdog.ps1 — ISA 看门狗（通用版）
# 从 C:\AI_exchange\skills\isa-process-handoff\ 提炼并参数化
#
# 功能：
# 1. 扫描 _system/signal_kill_*.json，执行 taskkill
# 2. 扫描 _system/signal_start_*.json，启动新进程
# 3. 检查心跳超时，触发交接
#
# 用法：powershell -ExecutionPolicy Bypass -File _isa/watchdog.ps1
# 可注册到 Windows Task Scheduler 定时运行

param(
    [string]$ProjectDir = ""
)

# 确定项目空间路径
if ($ProjectDir -eq "") {
    $ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

$SystemDir = Join-Path $ProjectDir "_system"
$AuditDir = Join-Path $ProjectDir "audit"
$LogsDir = Join-Path $ProjectDir "_logs"
$IsaDir = Join-Path $ProjectDir "_isa"

# 确保目录存在
foreach ($dir in @($SystemDir, $AuditDir, $LogsDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $logFile = Join-Path $LogsDir "watchdog.log"
    Add-Content -Path $logFile -Value "[$timestamp] $Message" -Encoding UTF8
}

# ── 处理 kill 信号 ──────────────────────────────────────────────
$killSignals = Get-ChildItem -Path $SystemDir -Filter "signal_kill_*.json" -ErrorAction SilentlyContinue
foreach ($signal in $killSignals) {
    try {
        $data = Get-Content $signal.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        $targetPid = $data.target_pid
        $reason = $data.reason

        Write-Log "Processing kill signal: PID=$targetPid, reason=$reason"

        # 尝试 taskkill
        $result = Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        if ($?) {
            Write-Log "Process $targetPid killed successfully"
        } else {
            Write-Log "Failed to kill process $targetPid (may already be dead)"
        }

        # 删除信号文件
        Remove-Item $signal.FullName -Force
        Write-Log "Signal file removed: $($signal.Name)"
    } catch {
        Write-Log "Error processing kill signal $($signal.Name): $_"
    }
}

# ── 处理 start 信号 ─────────────────────────────────────────────
$startSignals = Get-ChildItem -Path $SystemDir -Filter "signal_start_*.json" -ErrorAction SilentlyContinue
foreach ($signal in $startSignals) {
    try {
        $data = Get-Content $signal.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        $task = $data.task

        Write-Log "Processing start signal: task=$task"

        # 启动 handoff_executor.py
        $pythonExe = "python"
        $executorScript = Join-Path $IsaDir "handoff_executor.py"

        # 获取当前主进程 PID
        $roleTokenFile = Join-Path $AuditDir "role_token.json"
        $currentPid = 0
        if (Test-Path $roleTokenFile) {
            $token = Get-Content $roleTokenFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $currentPid = $token.primary_pid
        }

        if ($currentPid -gt 0) {
            Start-Process -FilePath $pythonExe `
                -ArgumentList "`"$executorScript`" --from-pid $currentPid --task `"$task`" --project-dir `"$ProjectDir`"" `
                -WorkingDirectory $ProjectDir `
                -WindowStyle Hidden
            Write-Log "Handoff executor started: old_pid=$currentPid, task=$task"
        } else {
            Write-Log "No primary PID found, cannot start handoff"
        }

        # 删除信号文件
        Remove-Item $signal.FullName -Force
        Write-Log "Signal file removed: $($signal.Name)"
    } catch {
        Write-Log "Error processing start signal $($signal.Name): $_"
    }
}

# ── 检查心跳超时 ────────────────────────────────────────────────
$heartbeatFile = Join-Path $AuditDir "heartbeat.json"
if (Test-Path $heartbeatFile) {
    try {
        $hb = Get-Content $heartbeatFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $lastHeartbeat = [DateTime]::Parse($hb.last_heartbeat)
        $elapsed = (Get-Date) - $lastHeartbeat

        if ($elapsed.TotalMinutes -gt 5) {
            Write-Log "Heartbeat timeout: last=$($hb.last_heartbeat), elapsed=$($elapsed.TotalMinutes)min"

            # 触发交接
            $task = "Heartbeat timeout recovery - $($elapsed.TotalMinutes) minutes since last heartbeat"
            $startSignalFile = Join-Path $SystemDir "signal_start_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
            @{
                task = $task
                requested_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            } | ConvertTo-Json | Set-Content -Path $startSignalFile -Encoding UTF8

            Write-Log "Auto start signal created for heartbeat timeout recovery"
        }
    } catch {
        Write-Log "Error checking heartbeat: $_"
    }
}

Write-Log "Watchdog cycle completed"