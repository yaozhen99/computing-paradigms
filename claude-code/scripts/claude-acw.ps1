#!/usr/bin/env pwsh
$env:ANTHROPIC_API_KEY = "sk-acw-901a135d-16d3bff2fdaa7d86"
$env:ANTHROPIC_BASE_URL = "https://api.aicodewith.com"
$env:ANTHROPIC_SMALL_FAST_MODEL = "claude-haiku-4-5-20251001"
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:API_TIMEOUT_MS = "600000"

if ($args.Count -gt 0 -and $args[0] -notmatch '^-') {
    $env:ANTHROPIC_MODEL = $args[0]
    $remaining = $args[1..($args.Count - 1)]
} else {
    $env:ANTHROPIC_MODEL = "claude-sonnet-4-6"
    $remaining = $args
}

Write-Host "[acw] $env:ANTHROPIC_MODEL"
$basedir = Split-Path $MyInvocation.MyCommand.Definition -Parent
& "$basedir/node_modules/@anthropic-ai/claude-code/bin/claude.exe" @remaining
exit $LASTEXITCODE
