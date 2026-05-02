#!/usr/bin/env python3
"""Quick verification script for GROQ setup in Kai."""

import os
import sys
from pathlib import Path

# Add parent directory to path so kai_agent can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kai_agent.ollama_client import OllamaClient


def verify_groq_setup():
    """Verify GROQ configuration is correct."""
    print("=" * 50)
    print("KAI GROQ SETUP VERIFICATION")
    print("=" * 50)

    # Check environment variables
    groq_env_key = os.environ.get("GROQ_API_KEY", "")
    kai_provider = os.environ.get("KAI_PROVIDER", "")
    kai_model = os.environ.get("KAI_MODEL", "")

    print(f"\n1. Environment Variables:")
    print(f"   GROQ_API_KEY: {'✓ SET' if groq_env_key else '✗ NOT SET (will use kai_config.json fallback)'}")
    print(f"   KAI_PROVIDER: {kai_provider or '✗ NOT SET'}")
    print(f"   KAI_MODEL: {kai_model or '✗ NOT SET'}")

    # Create client and check configuration
    print(f"\n2. OllamaClient Configuration:")
    client = OllamaClient()

    print(f"   Default provider: {client.provider}")
    print(f"   Default model: {client.model}")
    print(f"   GROQ API key loaded: {'✓ YES' if client.groq_api_key else '✗ NO'}")
    print(f"   GROQ base URL: {client.groq_base_url}")

    # Test provider switching to groq
    print(f"\n3. Provider Switching Test:")
    result = client.set_provider("groq", "llama3-8b-8192")
    print(f"   Switch to groq: {result}")

    print(f"   Current provider: {client.provider}")
    print(f"   Current model: {client.model}")
    print(f"   GROQ API key available: {'✓ YES' if client.groq_api_key else '✗ NO'}")

    # Test model switching
    print(f"\n4. Model Switching Test:")
    result = client.set_model("mixtral-8x7b-32768")
    print(f"   Switch model: {result}")

    # Verify API key format (basic check)
    print(f"\n5. API Key Validation:")
    if client.groq_api_key:
        key_prefix = client.groq_api_key[:10] + "..." if len(client.groq_api_key) > 10 else client.groq_api_key
        print(f"   Key prefix: {key_prefix}")
        print(f"   Key length: {len(client.groq_api_key)} chars")
        if client.groq_api_key.startswith("gsk_"):
            print(f"   Key format: ✓ VALID (starts with 'gsk_')")
        else:
            print(f"   Key format: ⚠ WARNING (does not start with 'gsk_')")
    else:
        print(f"   ✗ NO API KEY FOUND!")

    # Summary
    print(f"\n" + "=" * 50)
    if client.provider == "groq" and client.groq_api_key:
        print("RESULT: ✓ GROQ setup is COMPLETE and READY")
        print("\nYou can now use Kai with GROQ. Try commands like:")
        print("  /provider groq llama3-8b-8192")
        print("  /provider groq llama3-70b-8192")
        print("  /provider groq mixtral-8x7b-32768")
    else:
        print("RESULT: ✗ GROQ setup has ISSUES")
        if not client.groq_api_key:
            print("  - API key is missing")
        if client.provider != "groq":
            print("  - Provider is not set to groq")
    print("=" * 50)

    return client.provider == "groq" and bool(client.groq_api_key)


if __name__ == "__main__":
    success = verify_groq_setup()
    sys.exit(0 if success else 1)
