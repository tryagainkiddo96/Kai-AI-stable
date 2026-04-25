$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

cd $RepoRoot

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
}

Write-Host "Starting Kai AI Companion..." -ForegroundColor Cyan

# Fix for broken python paths
$env:PYTHONPATH = $RepoRoot

$arguments = $args -join ' '

try {
    if ($arguments) {
        python launch_kai_pentester.py $arguments
    } else {
        python launch_kai_pentester.py
    }
}
catch {
    Write-Host "Kai exited with error: $_" -ForegroundColor Red
    Start-Sleep 5
}
