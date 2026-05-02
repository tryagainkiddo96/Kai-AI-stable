#!/usr/bin/env python3
"""Live test of GROQ API connectivity with fixed headers."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kai_agent.ollama_client import OllamaClient


def test_groq_live():
    """Make a real API call to GROQ to verify the fix."""
    print("=" * 50)
    print("GROQ LIVE API TEST")
    print("=" * 50)

    client = OllamaClient()
    client.set_provider("groq", "llama-3.1-8b-instant")


    print(f"\nProvider: {client.provider}")
    print(f"Model: {client.model}")
    print(f"API Key loaded: {'YES' if client.groq_api_key else 'NO'}")
    print(f"Base URL: {client.groq_base_url}")

    # Simple test message
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Reply with a single short sentence."},
        {"role": "user", "content": "Say 'GROQ connection working' and nothing else."}
    ]

    print("\nSending test request...")
    try:
        reply = client.chat(messages, timeout=30)
        print(f"\n✓ SUCCESS! Response received:")
        print(f"  {reply}")
        return True
    except Exception as exc:
        print(f"\n✗ FAILED: {exc}")
        return False


if __name__ == "__main__":
    success = test_groq_live()
    print("\n" + "=" * 50)
    if success:
        print("RESULT: GROQ API is working correctly!")
    else:
        print("RESULT: GROQ API test failed.")
    print("=" * 50)
    sys.exit(0 if success else 1)
