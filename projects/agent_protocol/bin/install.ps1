# Agent Protocol Installer (PowerShell)
# Usage: .\install.ps1 -Target "C:\path\to\project"
#   or:  .\install.ps1 "C:\path\to\project"

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Target
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceTemplates = (Resolve-Path (Join-Path $ScriptDir "..\templates")).Path

if (-not (Test-Path $SourceTemplates)) {
    Write-Host "ERROR: Source templates not found: $SourceTemplates" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Target)) {
    $answer = Read-Host "Target directory does not exist. Create it? (y/n)"
    if ($answer -eq 'y') {
        New-Item -ItemType Directory -Path $Target -Force | Out-Null
        Write-Host "Created: $Target" -ForegroundColor Green
    } else {
        exit 1
    }
}

Write-Host "Installing Agent Protocol..." -ForegroundColor Green
Write-Host "Source: $SourceTemplates"
Write-Host "Target: $Target"
Write-Host ""

$conflictAction = $null

function Copy-WithConflictCheck {
    param([string]$Src, [string]$Dst)

    if (Test-Path $Dst) {
        if ($null -ne $conflictAction) {
            $choice = $conflictAction
        } else {
            Write-Host "File exists: $Dst" -ForegroundColor Yellow
            Write-Host "  [s] Skip  [o] Overwrite  [b] Backup then overwrite  [a] Overwrite all  [q] Quit"
            $choice = Read-Host "  Choose"
        }

        switch ($choice.ToLower()) {
            's' { Write-Host "  -> Skipped"; return $false }
            'o' { Write-Host "  -> Overwritten"; Remove-Item $Dst -Force -Recurse }
            'b' {
                $backup = "${Dst}.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
                Write-Host "  -> Backed up to $backup"
                Move-Item $Dst $backup -Force
            }
            'a' {
                $script:conflictAction = 'a'
                Write-Host "  -> Overwritten (all future conflicts auto-overwrite)" -ForegroundColor Cyan
                Remove-Item $Dst -Force -Recurse
            }
            'q' { Write-Host "  -> Install cancelled"; exit 0 }
            default { Write-Host "  -> Invalid choice, skipped"; return $false }
        }
    }

    Copy-Item $Src $Dst -Force
    Write-Host "  + Installed: $relativePath" -ForegroundColor Green
    return $true
}

Write-Host "Copying template files..."

Get-ChildItem -Path $SourceTemplates -Recurse | ForEach-Object {
    $srcPrefix = $SourceTemplates.TrimEnd('\', '/')
    $relativePath = $_.FullName.Substring($srcPrefix.Length).TrimStart('\', '/')
    $dstPath = Join-Path $Target $relativePath

    if ($_.PSIsContainer) {
        if (-not (Test-Path $dstPath)) {
            New-Item -ItemType Directory -Path $dstPath -Force | Out-Null
            Write-Host "  + Created dir: $relativePath\" -ForegroundColor Green
        }
    } else {
        $dstParent = Split-Path -Parent $dstPath
        if (-not (Test-Path $dstParent)) {
            New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
        }
        Copy-WithConflictCheck -Src $_.FullName -Dst $dstPath | Out-Null
    }
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "Agent Protocol installed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. cd $Target"
Write-Host "2. Review AGENTS.md for protocol rules"
Write-Host "3. Start your AI assistant - it will auto-read the protocol"
Write-Host ""
Write-Host "Tip: Add AGENTS.md and docs/ to version control" -ForegroundColor Yellow
