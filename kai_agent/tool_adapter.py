#!/usr/bin/env python3
# kai_agent/tool_adapter.py
# Tool adapter to convert Python functions to LLM function call format
# Adapted from KaliGPT's openai_tool_adapter.py
# Updated: 2026

import inspect
import typing
from typing import get_origin, get_args
import enum


def python_type_to_json_schema(annotation):
    """Convert Python type annotations to JSON Schema."""
    if annotation is inspect.Parameter.empty:
        return {"type": "string"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] or Union[T, None]
    if origin is typing.Union and type(None) in args:
        non_none = [a for a in args if a is not type(None)][0]
        return python_type_to_json_schema(non_none)

    # Literal values
    if origin is typing.Literal:
        return {
            "type": "string",
            "enum": list(args)
        }

    # Enum classes
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return {
            "type": "string",
            "enum": [e.value for e in annotation]
        }

    # Lists
    if origin in (list, typing.List):
        item_type = args[0] if args else str
        return {
            "type": "array",
            "items": python_type_to_json_schema(item_type)
        }

    # Dicts
    if origin in (dict, typing.Dict):
        return {
            "type": "object",
            "additionalProperties": True
        }

    # Scalars
    if annotation in (str,):
        return {"type": "string"}
    if annotation in (int, float):
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}

    # Fallback (safe default)
    return {"type": "string"}


def openai_tool_adapter(func):
    """Convert a Python function to OpenAI function calling format."""
    sig = inspect.signature(func)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        schema = python_type_to_json_schema(param.annotation)
        properties[name] = schema

        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (
                func.__doc__.strip().split("\n")[0]
                if func.__doc__
                else "No description available."
            ),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def ollama_tool_adapter(func):
    """Convert a Python function to Ollama tool format (JSON schema)."""
    openai_format = openai_tool_adapter(func)
    # Ollama uses similar format, just extract the function part
    return openai_format["function"]


def get_tool_schemas(functions, adapter="openai"):
    """Convert multiple functions to tool schemas.
    
    Args:
        functions: List of Python functions
        adapter: 'openai' or 'ollama'
    
    Returns:
        List of tool definitions
    """
    if adapter == "ollama":
        return [ollama_tool_adapter(f) for f in functions]
    return [openai_tool_adapter(f) for f in functions]


# Example usage:
if __name__ == "__main__":
    def example_tool(target: str, method: str = "nmap") -> str:
        """Run a scan on target with specified method."""
        pass

    def ping_tool(host: str, count: int = 4) -> bool:
        """Ping a host n times."""
        pass

    tools = get_tool_schemas([example_tool, ping_tool])
    import json
    print(json.dumps(tools, indent=2))
