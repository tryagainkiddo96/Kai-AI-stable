# Kai Terminal Start Guide

## Fastest Start

From the repo root:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
powershell -ExecutionPolicy Bypass -File tools\launch_kai_latest.ps1
```

This now starts the terminal-only Kai runtime.

## Canonical Windows Launcher

If you want the repo's standard launcher:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
.\run-kai.bat
```

## Start Just The Widget Server

If you want only the dashboard server path:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
powershell -ExecutionPolicy Bypass -File tools\launch_kai_widget.ps1
```

## Start The CLI Assistant Only

If you want terminal-only Kai directly without the wrapper:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
.\.venv\Scripts\python.exe -m kai_agent.assistant
```

Optional model override:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
.\.venv\Scripts\python.exe -m kai_agent.assistant --model gpt-5.4-mini
```

## First-Time Setup

Install Python deps:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
pip install -r requirements.txt
```

If the repo venv already exists, prefer:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Backend Check

Kai now defaults to the Codex-backed remote path. If you intentionally force local mode, verify Ollama is up:

```powershell
ollama list
ollama serve
```

Dashboard health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8127/api/health
```

Expected healthy dashboard response shape:

```json
{"ok": true, "service": "kai-widget", "surface": "dashboard-only", ...}
```

## Useful Environment Overrides

```powershell
$env:KAI_PROVIDER = "codex"
$env:KAI_MODEL = "gpt-5.4-mini"
$env:KAI_MAX_HISTORY = "6"
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:KAI_SKIP_BROWSER = "1"
```

Then launch:

```powershell
powershell -ExecutionPolicy Bypass -File tools\launch_kai_latest.ps1
```

## Common Problems

Terminal launcher does not start:

```powershell
.\.venv\Scripts\python.exe -m kai_agent.assistant
```

Remote Codex path slow or unavailable:

```powershell
ollama serve
ollama list
```

Check the running Kai process:

```powershell
Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*kai_agent.widget_server*"
} | Select-Object ProcessId, ParentProcessId, Name, CommandLine
```

Dashboard does not open:

```powershell
powershell -ExecutionPolicy Bypass -File tools\launch_kai_widget.ps1
```

## Best Default

Use this unless you specifically want the CLI:

```powershell
cd "C:\Users\7nujy6xc\OneDrive\Desktop\03-Projects\Kai-AI"
powershell -ExecutionPolicy Bypass -File tools\launch_kai_latest.ps1
```
