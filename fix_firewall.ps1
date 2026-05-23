# Check if Python is blocked by firewall
Write-Host "Checking Windows Firewall rules for Python..." -ForegroundColor Cyan

# Find Python executable path
$pythonPath = (Get-Command python).Source
Write-Host "Python path: $pythonPath" -ForegroundColor Gray

# Check for existing rules
$existing = netsh advfirewall firewall show rule name="Python HTTP" verbose 2>&1
if ($existing -match "Rule Name") {
    Write-Host "✓ Firewall rule 'Python HTTP' already exists" -ForegroundColor Green
} else {
    Write-Host "! No firewall rule found. Adding..." -ForegroundColor Yellow
    
    # Check if we have admin rights
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host ""
        Write-Host "⚠  Need Administrator privileges to add firewall rule." -ForegroundColor Red
        Write-Host ""
        Write-Host "Please run this script AS ADMINISTRATOR:" -ForegroundColor Yellow
        Write-Host "  1. Right-click this file" -ForegroundColor White
        Write-Host "  2. Select 'Run with PowerShell'" -ForegroundColor White
        Write-Host ""
        Write-Host "Or run this command manually as Admin:" -ForegroundColor Yellow
        Write-Host "  netsh advfirewall firewall add rule name=""Python HTTP"" dir=in action=allow program=""$pythonPath"" enable=yes" -ForegroundColor White
        exit 1
    }
    
    # Add the rule
    netsh advfirewall firewall add rule name="Python HTTP" dir=in action=allow program="$pythonPath" enable=yes
    Write-Host "✓ Firewall rule added!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Testing if port 5555 is reachable..." -ForegroundColor Cyan
Write-Host ""
Write-Host "1. First start the server in ANOTHER terminal:" -ForegroundColor Yellow
Write-Host "   python kai_web_ui.py" -ForegroundColor White
Write-Host ""
Write-Host "2. Then come back here and run:" -ForegroundColor Yellow
Write-Host "   Test-NetConnection -ComputerName 127.0.0.1 -Port 5555" -ForegroundColor White
Write-Host ""
Write-Host "If TcpTestSucceeded shows True, the browser will work." -ForegroundColor Cyan
