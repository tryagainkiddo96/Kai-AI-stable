#!/usr/bin/env python3
"""KAI Enterprise API - FastAPI server."""

import asyncio
import json
import logging
import os
from collections.abc import Mapping
from datetime import datetime
from functools import lru_cache

import uvicorn
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from kai_enterprise import KaiEnterprise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KAI-API")


def _load_allowed_origins() -> list[str]:
    raw_value = os.getenv("KAI_API_ALLOWED_ORIGINS", "")
    if not raw_value:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            origins = [str(item).strip() for item in parsed if str(item).strip()]
            if origins:
                return origins
    except json.JSONDecodeError:
        origins = [item.strip() for item in raw_value.split(",") if item.strip()]
        if origins:
            return origins
    raise RuntimeError("KAI_API_ALLOWED_ORIGINS must be a JSON array or comma-separated string")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)


class PluginRequest(BaseModel):
    plugin: str = Field(min_length=1, max_length=128)
    args: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class MemoryStoreRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    category: str = Field(default="general", max_length=128)
    tags: str = Field(default="", max_length=1024)


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    category: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=5, ge=1, le=50)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


@lru_cache(maxsize=1)
def get_kai() -> KaiEnterprise:
    return KaiEnterprise()


def _coerce_plugin_args(args: Mapping[str, object]) -> dict[str, object]:
    return {str(key): value for key, value in args.items()}


app = FastAPI(
    title="Kai Enterprise API",
    version="1.0.0",
    description="Production-grade AI assistant with plugins, memory, and project management",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

connected_clients: set[WebSocket] = set()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "status": "running",
        "service": "Kai Enterprise",
        "version": "1.0.0",
    }


@app.post("/api/ask")
async def ask(request: AskRequest) -> dict[str, str]:
    response = await asyncio.to_thread(get_kai().ask_stateless, request.question)
    return {
        "question": request.question,
        "answer": response,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/plugin")
async def execute_plugin(request: PluginRequest) -> dict[str, object]:
    args = _coerce_plugin_args(request.args)
    result = await asyncio.to_thread(get_kai().plugin_manager.execute, request.plugin, **args)
    return {
        "plugin": request.plugin,
        "args": args,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/plugins")
async def list_plugins() -> dict[str, object]:
    kai = get_kai()
    return {
        "plugins": list(kai.plugin_manager.plugins.keys()),
        "descriptions": {
            name: plugin.get_description()
            for name, plugin in kai.plugin_manager.plugins.items()
        },
    }


@app.post("/api/memory/store")
async def store_memory(request: MemoryStoreRequest) -> dict[str, str]:
    await asyncio.to_thread(get_kai().memory.store, request.content, request.category, request.tags)
    return {
        "status": "stored",
        "category": request.category,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/memory/search")
async def search_memory(request: MemorySearchRequest) -> dict[str, object]:
    results = await asyncio.to_thread(get_kai().memory.search, request.query, request.category, request.limit)
    return {
        "query": request.query,
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/project/create")
async def create_project(request: ProjectCreateRequest) -> dict[str, str]:
    result = await asyncio.to_thread(get_kai().project_manager.create_project, request.name)
    return {
        "status": "created",
        "project": request.name,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/projects")
async def list_projects() -> dict[str, object]:
    kai = get_kai()
    projects = kai.project_manager.list_projects()
    return {
        "projects": projects.split("\n") if projects != "No projects" else [],
        "current": kai.project_manager.current_project,
    }


@app.get("/api/history")
async def get_history(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, object]:
    kai = get_kai()
    history = kai.history[-limit:]
    return {
        "history": history,
        "total": len(kai.history),
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("Client connected. Total: %s", len(connected_clients))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON payload"}))
                continue

            if not isinstance(message, dict):
                await websocket.send_text(json.dumps({"error": "Payload must be a JSON object"}))
                continue

            question = message.get("question", "")
            if not isinstance(question, str) or not question.strip():
                await websocket.send_text(json.dumps({"error": "No question"}))
                continue
            if len(question) > 8000:
                await websocket.send_text(
                    json.dumps({"error": "Question must be under 8000 characters"})
                )
                continue

            response = await asyncio.to_thread(get_kai().ask_stateless, question)
            await websocket.send_text(
                json.dumps(
                    {
                        "question": question,
                        "answer": response,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info("Client disconnected. Total: %s", len(connected_clients))
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        connected_clients.discard(websocket)


def main() -> None:
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("Starting Kai Enterprise API on %s:%s", host, port)
    logger.info("Docs: http://localhost:%s/docs", port)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
