$ErrorActionPreference = "Stop"
$RepoRoot = "C:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI"

cd $RepoRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         KAI AI COMPANION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "$RepoRoot;$RepoRoot\kai_agent"


$arguments = $args -join ' '

try {
    if ($arguments -ne "") {
        python scripts/launch_kai_pentester.py $arguments
    } else {
        python kai_agent/kai_dashboard.py
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
