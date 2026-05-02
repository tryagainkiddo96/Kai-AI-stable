import sys
from pathlib import Path
from kai_agent.ollama_client import OllamaClient


def main() -> int:
    # Use defaults so this script can be run standalone
    client = OllamaClient()
    if client.is_reachable(timeout=2):
        print(f"Ollama reachable at {client.base_url} (model={client.model})")
        return 0
    else:
        print(f"Ollama NOT reachable at {client.base_url} (model={client.model})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
