# Kai Hung Process Cleaner
# Kills hung VS Code: processes and other stale processes

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   HUNG PROCESS CLEANER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$killed = @()

# 1. Kill Code.exe processes without a window title (orphaned/background)
Write-Host "[1/4] Checking for orphaned VS Code: processes..." -ForegroundColor Yellow
$codeProcesses = Get-Process -Name "Code" -ErrorAction SilentlyContinue
$currentPid = $PID
foreach ($proc in $codeProcesses) {
    try {
        $title = $proc.MainWindowTitle
        $id = $proc.Id
        # Skip if it's the current PowerShell process tree
        if ($id -eq $currentPid) { continue }
        
        # Kill processes with empty window titles (likely orphaned)
        if ([string]::IsNullOrWhiteSpace($title)) {
            Write-Host "  Killing orphaned Code.exe PID $id (no window title)" -ForegroundColor Red
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            $killed += "Code.exe (PID $id, orphaned)"
        }
    } catch {}
}

# 2. Kill excess Code.exe - if more than 8 remain, kill oldest ones
Write-Host ""
Write-Host "[2/4] Checking for excess VS Code: processes..." -ForegroundColor Yellow
$codeProcesses = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Sort-Object StartTime
$count = ($codeProcesses | Measure-Object).Count
if ($count -gt 8) {
    $toKill = $count - 8
    Write-Host "  Found $count Code.exe processes. Killing $toKill oldest..." -ForegroundColor Red
    $skippedCurrent = $false
    foreach ($proc in $codeProcesses) {
        if ($toKill -le 0) { break }
        try {
            if ($proc.Id -eq $currentPid) { continue }
            Write-Host "  Killing Code.exe PID $($proc.Id) (started: $($proc.StartTime))" -ForegroundColor Red
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            $killed += "Code.exe (PID $($proc.Id), excess)"
            $toKill--
        } catch {}
    }
} else {
    Write-Host "  Only $count Code.exe processes found - within normal range" -ForegroundColor Green
}

# 3. Kill other stale processes
Write-Host ""
Write-Host "[3/4] Checking for other stale processes..." -ForegroundColor Yellow
$targets = @("python", "python3", "node", "kai", "docker")
foreach ($target in $targets) {
    $procs = Get-Process -Name $target -ErrorAction SilentlyContinue
    foreach ($proc in $procs) {
        try {
            # Kill if running longer than 2 hours and using high CPU or no window
            $runtime = (Get-Date) - $proc.StartTime
            if ($runtime.TotalHours -gt 2) {
                Write-Host "  Killing stale $($proc.ProcessName).exe PID $($proc.Id) (running $($runtime.ToString('hh\:mm')))" -ForegroundColor Red
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                $killed += "$($proc.ProcessName).exe (PID $($proc.Id), stale)"
            }
        } catch {}
    }
}

# 4. Kill explicitly not-responding processes
Write-Host ""
Write-Host "[4/4] Checking for Not Responding processes..." -ForegroundColor Yellow
$notResponding = Get-Process | Where-Object { $_.Responding -eq $false }
foreach ($proc in $notResponding) {
    try {
        Write-Host "  Killing not-responding $($proc.ProcessName) PID $($proc.Id)" -ForegroundColor Red
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $killed += "$($proc.ProcessName) (PID $($proc.Id), not responding)"
    } catch {}
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if ($killed.Count -eq 0) {
    Write-Host "No processes needed to be killed." -ForegroundColor Green
} else {
    Write-Host "Killed $($killed.Count) process(es):" -ForegroundColor Green
    foreach ($k in $killed) {
        Write-Host "  - $k" -ForegroundColor Gray
    }
}
Write-Host ""

