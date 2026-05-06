#!/usr/bin/env pwsh
$env:ANTHROPIC_API_KEY = ""
$env:ANTHROPIC_AUTH_TOKEN = "sk-4b266b0d02564bdd8b91bee9e1fb773e"
$env:ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"
$env:ANTHROPIC_SMALL_FAST_MODEL = "deepseek-v4-flash"
$env:ANTHROPIC_MAX_CONTEXT_TOKENS = "1000000"
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:API_TIMEOUT_MS = "600000"

if ($args.Count -gt 0 -and $args[0] -notmatch '^-') {
    $env:ANTHROPIC_MODEL = $args[0]
    $remaining = $args[1..($args.Count - 1)]
} else {
    $env:ANTHROPIC_MODEL = "deepseek-v4-pro"
    $remaining = $args
}

Write-Host "[deepseek] $env:ANTHROPIC_MODEL (1M context)"
$basedir = Split-Path $MyInvocation.MyCommand.Definition -Parent
& "$basedir/node_modules/@anthropic-ai/claude-code/bin/claude.exe" @remaining
exit $LASTEXITCODE
