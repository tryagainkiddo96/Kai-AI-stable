"""Lightweight Mac chat API for Kai.

This provides a minimal REST API to communicate with Kai from other devices.
Run with: uvicorn kai_agent.mac_chat_api:app --host 0.0.0.0 --port 8000
This is a deliberately small, safe interface designed for inter-machine use
within a trusted network.
"""
from __future__ import annotations

import os
from pathlib import Path
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

from kai_agent.assistant import KaiAssistant

app = FastAPI(title="Kai Mac Chat API")

class TextRequest(BaseModel):
    text: str

_assistant: KaiAssistant | None = None

def _get_assistant() -> KaiAssistant:
    global _assistant
    if _assistant is None:
        model = os.environ.get("KAI_MODEL", "sam860/dolphin3-llama3.2:3b")
        workspace = Path(os.environ.get("KAI_WORKSPACE", str(Path.home() / "Kai-AI")))
        _assistant = KaiAssistant(model=model, workspace=workspace)
    return _assistant

@app.post("/ai")
async def ai_endpoint(req: TextRequest):
    assistant = _get_assistant()
    reply = await assistant.ask(req.text)
    return {"reply": reply}
