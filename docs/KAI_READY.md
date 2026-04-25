# Kai Ready

## Canonical Runtime

Kai is ready through the stable widget/dashboard path:

```powershell
powershell -ExecutionPolicy Bypass -File tools/launch_kai_latest.ps1
```

Primary surface:

- Dashboard: `http://127.0.0.1:8127`
- Canonical repo launcher: `run-kai.bat`
- Quiet Windows launcher: `Start-Kai.vbs`

## What This Repo Treats As Primary

- Brain: `kai_agent/assistant.py`
- Dashboard server: `kai_agent/widget_server.py`
- Browser UI: `widget/kai-unified-dashboard.html`

Legacy entrypoints are archived under `archive/root_clutter/legacy_entrypoints/`; old dashboards and launcher variants are not the primary runtime.

## What Is Working

- Chat with local fallback behavior
- Screen OCR and active-window OCR
- WiFi, Bluetooth, and current-link device discovery
- Kali session controls
- Memory, policy, and task flows
- Watcher and TTS controls

## What Was Recently Hardened

- Simple math/date/day prompts answer without waiting on the model
- Chat fallback now prefers useful degraded answers over raw timeout-style failures
- Widget polling pauses while the tab is hidden
- Fast widget replies now update Kai state/history correctly
- Pending proactive messages are cursor-based, so one tab does not drain them for all others
- Screen OCR no longer reuses stale capture files

## Current Caveats

- Enterprise/runtime drift still exists in parts of the repo outside the stable widget path
- The dashboard shell is improved, but a larger visual/flow redesign is still in progress
- Some legacy docs and legacy surfaces still need consolidation

## Recommended Next Start Check

1. Launch Kai with `run-kai.bat`
2. Open `http://127.0.0.1:8127`
3. Test:
   - `10 + 10`
   - `what day is it`
   - `what is python`
   - `scan the network`
   - `read my screen`
