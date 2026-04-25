#!/usr/bin/env python3
"""
Kai Launch Diagnostic — run this to find out why Kai isn't responding
"""

import sys
import os
import json
from urllib import error, request

# Add project to path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

print("=" * 60)
print("  KAI LAUNCH DIAGNOSTIC")
print("=" * 60)

# 1. Check Python environment
print(f"\n1. Python: {sys.version}")
print(f"   Executable: {sys.executable}")

# 2. Check kai_agent import
print("\n2. Checking kai_agent module...")
try:
    from kai_agent.assistant import KaiAssistant
    print("   ✅ kai_agent.assistant imports OK")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# 3. Check Ollama connection
print("\n3. Checking Ollama connection...")
ollama_host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
print(f"   Host: {ollama_host}")

try:
    req = request.Request(
        f"{ollama_host}/api/tags",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    with request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        print(f"   ✅ Ollama is running")
        print(f"   Available models: {models}")
except error.URLError as e:
    print(f"   ❌ Ollama not reachable: {e}")
    print("\n   FIX: Start Ollama with 'ollama serve' or check the system tray icon")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# 4. Check target model
print("\n4. Checking target model...")
from kai_agent.ollama_client import OllamaClient
client = OllamaClient()

print(f"   Target model: {client.model}")
if client.has_model(client.model, timeout=5):
    print(f"   ✅ Model '{client.model}' is available")
else:
    available = client.list_models(timeout=5)
    print(f"   ❌ Model '{client.model}' NOT found")
    print(f"   Available: {available}")
    if available:
        print(f"\n   FIX: Use --model {available[0]} when launching Kai")
    else:
        print(f"\n   FIX: Pull a model with 'ollama pull llama3.2:3b'")
    sys.exit(1)

# 5. Quick chat test
print("\n5. Testing chat (sending 'hello' to model)...")
try:
    response = client.chat(
        [{"role": "user", "content": "Say 'OK' and nothing else."}],
        timeout=30,
    )
    print(f"   ✅ Model responded: '{response.strip()[:60]}'")
except Exception as e:
    print(f"   ❌ Chat failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("  ALL CHECKS PASSED — Kai should work!")
print("=" * 60)
print("\nLaunch Kai with:")
print("   python -m kai_agent.assistant")
