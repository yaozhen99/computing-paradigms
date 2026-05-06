#!/usr/bin/env pwsh
$env:ANTHROPIC_AUTH_TOKEN = "2eb8e6c687fbb47b855a82e8a5e81533:MjU3ZjM3NjkwZjc0MTViOTFmYmVhNWQx"
$env:ANTHROPIC_BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic"
$env:ANTHROPIC_MODEL = "astron-code-latest"
$env:ANTHROPIC_SMALL_FAST_MODEL = "astron-code-latest"
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
$env:API_TIMEOUT_MS = "600000"

Write-Host "[xfyun] astron-code-latest"
$basedir = Split-Path $MyInvocation.MyCommand.Definition -Parent
& "$basedir/node_modules/@anthropic-ai/claude-code/bin/claude.exe" @args
exit $LASTEXITCODE
