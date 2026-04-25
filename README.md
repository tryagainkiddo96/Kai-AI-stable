# Kai

A local-first AI assistant inspired by a Shiba Inu named Kai.

Kai now runs on a stable terminal-first foundation. The active runtime is one assistant brain with an optional browser control surface.
Computer access is part of the local codebase through Kai's desktop, shell, screen, file, and browser tooling, all gated by tool policy:

- `kai_agent/assistant.py` is the primary assistant brain
- `widget/kai-unified-dashboard.html` is the optional browser control surface
- `tools/launch_kai_latest.ps1` starts the stable terminal path
- legacy 3D/stack launchers now redirect to the stable terminal path by default
- preserved legacy launchers live under `tools/legacy/`
- `bridge/` is transport, not a second brain

Canonical structure notes live in [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

## What's inside

```text
kai_agent/          Python-side Kai brain (Codex/Ollama, memory, tools)
bridge/             WebSocket event bridge
kai_companion/      Legacy experimental 3D surface (not part of default runtime)
widget/             Unified browser dashboard and static assets
tools/              Launchers, rigging, texture workflows
memory/             Persistent notes and session history
```

## Identity

- Breed: Shiba Inu
- Coat: Black and tan
- Markings: White/cream chest, muzzle, and paw accents
- Style: Realistic 3D desktop companion with procedural animation

## Design system

All UI surfaces share a warm Shiba Inu palette:

| Token | Hex | Description |
|-------|-----|-------------|
| `kai-charcoal` | `#1A1612` | Deep background (black coat) |
| `kai-rust` | `#C4783A` | Primary accent (tan markings) |
| `kai-amber` | `#D4943A` | Secondary accent |
| `kai-chest` | `#F5E6D0` | Text / cream markings |
| `kai-cream` | `#FFF5E1` | Bright text |

Applied to the web widget and stable dashboard surface.

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Runtime notes:

- `bridge/server.py` hosts the websocket event bridge on `ws://127.0.0.1:8765`
- `kai_agent/emit_event.py` sends `kai_thinking`, `kai_walk`, `kai_sleep`, or `kai_wag_tail`
- `kai_agent/assistant.py` runs a terminal Kai CLI backed by Codex or Ollama
- `memory/` stores lightweight persistent notes and session history for Kai

Single-brain rule:

- tool execution should flow through `KaiAssistant -> DesktopTools -> ToolPolicy`
- legacy panel and companion surfaces are not part of the default runtime
- the CLI is the default operator surface
- the stable widget server is optional when you need browser controls

### 2. Launch Kai

**Easiest way — Desktop Launcher:**

Double-click `Launch Kai.bat` on your Desktop for a menu-driven launcher.

**Manual launch:**

```powershell
# Beautiful Terminal Dashboard (recommended)
python kai_dashboard.py

# Or use the Windows launcher
launch_dashboard.bat

# Terminal-only Kai (classic)
powershell -ExecutionPolicy Bypass -File tools/launch_kai_latest.ps1

# Widget server only
powershell -ExecutionPolicy Bypass -File tools/launch_kai_widget.ps1
```
### 3. Chat

Use the terminal session that opens from the launcher.

For the Windows launcher, use `Start-Kai.vbs` on the Desktop. It now opens a visible terminal session for Kai.

## Dashboard

The `kai_dashboard.py` provides a beautiful terminal UI with:

- Colorful panels and styled messages
- Interactive menu (`/menu` or type menu options)
- Quick provider/model switching
- Chat history with syntax highlighting
- Keyboard shortcuts for common commands

### Dashboard commands

| Command | What it does |
|---------|-------------|
| `/menu` | Show interactive menu |
| `/provider <name> [model]` | Switch LLM provider (ollama, deepseek, hf, codex) |
| `/model <name>` | Change model |
| `/clear` | Clear chat history |
| `/help` | Show all commands |

### Dashboard shortcuts (in menu)

| Key | Action |
|-----|--------|
| `P` | Provider menu |
| `M` | Model menu |
| `C` | Clear chat |
| `H` | Help |
| `Q` | Quit |

## Unified dashboard

Optional browser surface with live:

- chat
- mood, health, and status
- Kali terminal controls
- OCR and watcher controls
- TTS controls
- signal map and RF telemetry
- integrated pentesting lab

Legacy browser pages are optional compatibility surfaces. The stable foundation is the unified dashboard only.

## Chat commands

| Command | What it does |
|---------|-------------|
| `/remember <text>` | Save something for Kai to learn |
| `/memory` | Show stored memory |
| `/screen` | Capture screen + OCR |
| `/run <cmd>` | Run a shell command |
| `/read <file>` | Read a file |
| `/ls <path>` | List files |
| `/policy status` | Show capability policy mode |
| `/policy mode <power-user\|balanced\|guarded>` | Change capability policy mode |
| `/capabilities` | List Kai's explicit tool catalog |
| `/autonomy on` | Enable guarded autonomy |
| `/autonomy tick` | Run one autonomous step |
| `/autonomy off` | Disable autonomy |

## Recovery mode

When a tool step fails, Kai builds a recovery summary:

- Failure point
- Likely cause
- Smallest fix
- Next command to try

When the primary model fails, Kai auto-recovers:

1. Fallback local models
2. Live web research if `TAVILY_API_KEY` is set

Set `KAI_FALLBACK_MODELS=qwen3:4b-q4_K_M,llama2:latest` to customize.

## 3D model

### Assets

| File | Role |
|------|------|
| `kai_textured.glb` | Canonical photo-replica runtime identity |
| `kai_textured_rigged.glb` | Provisional rigged candidate |
| `kai-lite.glb` | Motion reference donor only |
| `kai_mixamo_ready.fbx` | Staging file for Mixamo auto-rig |

### Rigging pipeline

1. Upload `kai_mixamo_ready.fbx` to [Mixamo](https://www.mixamo.com)
2. Auto-rig with marker placement
3. Download rigged result as `kai_mixamo_rigged_source.fbx`
4. Run rig prep:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare_kai_rig_runtime.ps1
```

5. Export validated `kai_textured_rigged.glb`

### Texturing workflow

```bash
blender kai_companion/assets/kai/kai_texture_workspace.blend
blender -b --python tools/export_kai_runtime_glb.py
blender -b --python tools/render_kai_texture_preview.py
```

## Checkpoint and restore

```powershell
powershell -ExecutionPolicy Bypass -File tools/checkpoint_kai.ps1 -Name before-upgrade
powershell -ExecutionPolicy Bypass -File tools/restore_kai_checkpoint.ps1 -Branch codex/before-upgrade
```

## Logs

Structured interaction logs are written to `logs/events.jsonl`. The desktop panel has an `OPEN LOGS` button.

## Notes

- Default model: `qwen3:4b-q4_K_M` for lighter systems
- For heavier models, try `python -m kai_agent.assistant --model <model>`
- Set `TAVILY_API_KEY` for live web research
- The companion only loads `kai_textured.glb` as runtime identity
- `KAI_FALLBACK_MODELS` controls fallback model order, for example `qwen3:4b-q4_K_M,llama2:latest,mistral:latest`
- `power-user` is permissive local operator mode, `balanced` blocks medium-risk actions for review, and `guarded` is read-mostly
- During autonomous ticks, Kai only runs low-risk actions and persists autonomy state in `memory/autonomy.json`
