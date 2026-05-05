# Netdef Rule Cleanup Utility
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Netdef: Rule Cleanup Utility" -ForegroundColor White
Write-Host "   Preview & Remove Custom Rules" -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INFO] Scanning for custom firewall rules..." -ForegroundColor Cyan
Write-Host ""

$rules = Get-NetFirewallRule | Where-Object {
    $_.DisplayName -like 'Allow*' -or
    $_.DisplayName -like 'Wail2Ban*' -or
    $_.DisplayName -like 'Block*' -or
    $_.DisplayName -like 'Allow ALL*' -or
    $_.DisplayName -like 'Allow Trusted*' -or
    $_.DisplayName -like 'Allow Outbound*' -or
    $_.DisplayName -like 'Block TCP*' -or
    $_.DisplayName -like 'Block UDP*' -or
    $_.DisplayName -like 'Block Outbound*'
}

if ($rules -ne $null) {
    $ruleArray = @($rules)
    $count = $ruleArray.Count
    Write-Host "Found $count custom rule(s):" -ForegroundColor Green
    Write-Host ""
    $ruleArray | Format-Table DisplayName, Direction, Action, Enabled -AutoSize
} else {
    Write-Host "No custom rules found." -ForegroundColor Yellow
}

Write-Host ""
$confirm = Read-Host 'Confirm delete all rules? (Y/N)'

if ($confirm -eq 'Y' -or $confirm -eq 'y') {
    if ($rules -ne $null) {
        $rules | Remove-NetFirewallRule -Confirm:$false
        Write-Host 'Rules deleted.' -ForegroundColor Green
    } else {
        Write-Host 'No rules to delete.' -ForegroundColor Yellow
    }
} else {
    Write-Host 'Operation cancelled.' -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Press any key to exit..." -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')