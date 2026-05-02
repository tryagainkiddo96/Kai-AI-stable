<#
Cross-platform launcher for Kai (PowerShell).
Usage:
- From repo root: .\scripts\launch_kai.ps1 -Model sam860/dolphin3-llama3.2:3b -Workspace "C:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI"
#>
param(
  [string]$Model = "sam860/dolphin3-llama3.2:3b",
  [string]$Workspace = "$(Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) '..')"
)

Write-Host "[Kai Launcher] Starting Kai..." -ForegroundColor Green
"Workspace: $Workspace" | Write-Host

if (-not (Test-Path $Workspace)) {
  New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
}

## Ensure Python path includes repo root for imports
$repoRoot = (Get-Location).Path
$env:PYTHONPATH = "$repoRoot;$env:PYTHONPATH"

python -m kai_agent.assistant --model $Model --workspace $Workspace
