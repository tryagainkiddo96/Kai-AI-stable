import asyncio
from kai_agent.assistant import KaiAssistant
from pathlib import Path

async def test_functions():
    assistant = KaiAssistant(model="llama3.2:3b", workspace=Path("."))
    commands = [
        "Hello Kai",
        "/memory",
        "/mood",
        "/remember Test memory entry",
        "/analyze print('hello')",
        "/provider ollama",
        "/model llama3.2:3b"
    ]
    results = {}
    for cmd in commands:
        try:
            reply = await assistant.ask(cmd)
            results[cmd] = reply
        except Exception as e:
            results[cmd] = f"Error: {str(e)}"
    return results

if __name__ == "__main__":
    results = asyncio.run(test_functions())
    print(results)