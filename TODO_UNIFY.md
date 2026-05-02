# Kai AI - Unification Plan

## Goal
Unify launch files to work seamlessly on both Windows and WSL/Linux environments.

---

## Issues Identified

### Issue 1: Missing Root-Level Dashboard
- **Current**: `kai_dashboard.py` exists only at `kai_agent/kai_dashboard.py`
- **Expected by README**: `python kai_dashboard.py` (root level)
- **Fix**: Create root-level wrapper

### Issue 2: Batch Files Point to Wrong Locations
- `scripts/launch_dashboard.bat` → `python kai_dashboard.py` (doesn't exist)
- `scripts/run_kai_ollama.bat` → `python kai_agent/kai_dashboard.py`
- **Fix**: Update all batch files to use correct paths

### Issue 3: Shell Scripts Have Hardcoded WSL Paths
- `scripts/run_kai_groq.sh` → hardcoded `/mnt/c/Users/...` path
- `scripts/launch_kai_pentester.sh` → hardcoded `launch_kai_pentester.py`
- **Fix**: Use relative paths, detect environment

### Issue 4: README Outdated
- Says `python kai_dashboard.py` but file is at `kai_agent/kai_dashboard.py`
- **Fix**: Update instructions

---

## Tasks

### Phase 1: Create Root-Level Launchers

- [ ] **1.1** Create `kai_dashboard.py` at root (wrapper that imports from kai_agent)
- [ ] **1.2** Create unified launcher script that works on all platforms

### Phase 2: Fix Batch Files

- [ ] **2.1** Update `scripts/launch_dashboard.bat`
- [ ] **2.2** Update `scripts/run_kai_ollama.bat`
- [ ] **2.3** Update `scripts/run_kai_deepseek.bat`
- [ ] **2.4** Update `scripts/run_kai_groq.bat`

### Phase 3: Fix Shell Scripts

- [ ] **3.1** Create `scripts/run_kai_unified.sh` (cross-platform)
- [ ] **3.2** Fix `scripts/run_kai_groq.sh`
- [ ] **3.3** Fix `scripts/launch_kai_pentester.sh`

### Phase 4: Update Documentation

- [ ] **4.1** Update README.md with correct paths
- [ ] **4.2** Update any other documentation

---

## Implementation Notes

### Cross-Platform Detection
```python
import sys
import os

def get_workspace_root():
    # Detect WSL
    if os.path.exists('/mnt/c'):
        return '/mnt/c/Users/youruser/OneDrive/Desktop/Kai-AI'
    # Windows
    if os.name == 'nt':
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Linux/macOS
    return os.path.expanduser('~/Kai-AI')
```

### Unified Shell Launcher
```bash
#!/bin/bash
# Auto-detect environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
