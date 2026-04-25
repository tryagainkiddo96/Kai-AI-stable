# Kai Quick Reference

**Kai** is a local AI assistant with a terminal-first runtime and an optional browser surface.

## One-Line Start

```bash
powershell -ExecutionPolicy Bypass -File tools/launch_kai_latest.ps1
```

This launches the terminal-only Kai runtime, shuts down legacy panel/widget surfaces first, and keeps the default path light on RAM.

`tools/launch_kai_widget.ps1` still starts the browser dashboard when you want it. Legacy `launch_kai_stack.ps1`, `launch_kai_3d.ps1`, and `launch_kai_hologram.ps1` now redirect to the stable path. Preserved legacy launchers live under `tools/legacy/`.

On Windows, `run-kai.bat` is the canonical repo launcher and `Start-Kai.vbs` is the quiet Desktop launcher.

---

## What Kai Can Do

| What | How |
|------|-----|
| **Chat** | Type directly in the terminal |
| **Screen capture** | `"capture the screen"` or `/screen` |
| **WiFi/Bluetooth** | `"scan wifi"` or `"scan bluetooth"` |
| **File ops** | `/read path/to/file` or `"find doc.pdf"` |
| **Tasks** | `"do task: [description]"` → auto-plans & executes |
| **Autonomy** | `/autonomy on` then `/autonomy tick` |
| **Memory** | `/remember [text]` to save notes |
| **Policy** | `/policy status` to check permissions |

---

## File Structure

```
kai_agent/          ← Brain (Codex/Ollama-backed Python)
widget/             ← Stable web chat + ops UI
kai_companion/      ← Legacy experimental surface (inactive by default)
bridge/             ← Optional transport
tools/              ← Launch scripts
memory/             ← Persistent state & notes
```

---

## Key Commands

```
/screen                        Screenshot + OCR
/run <shell command>           Execute command
/read <file>                   Read file
/ls <path>                     List directory
/remember <text>               Save to memory
/memory                        Show saved notes
/policy status                 Show capability mode
/policy mode power-user        Unlock all tools
/autonomy on                   Enable autonomous mode
/capabilities                  List all tools
```

---

## Natural Language Works Too

```
"what do you see?"             → Captures & analyzes screen
"scan the network"             → Network tools
"get me that download"         → Web search + download
"do task: [something]"         → Multi-step task
```

---

## Troubleshoot

| Issue | Fix |
|-------|-----|
| Kai not responding | Check Codex auth first; if forcing local mode, check `ollama list` and `ollama serve` |
| Need the dashboard anyway | Run: `powershell -ExecutionPolicy Bypass -File tools/launch_kai_widget.ps1` |
| Tools blocked | `/policy mode power-user` to unlock |
| Need logs | `tail -f logs/events.jsonl` |

---

## Settings

Set via environment:
```powershell
$env:KAI_PROVIDER = "codex"                # Default remote backend
$env:KAI_MODEL = "gpt-5.4-mini"            # Fast Codex-backed chat model
$env:KAI_MAX_HISTORY = "4"                 # Conversation history length
$env:KAI_CODEX_REASONING_EFFORT = "low"    # Keep chat latency down
```

---

See **CAPABILITIES.md** for full feature list and examples.
