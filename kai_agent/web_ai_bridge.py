"""
Web AI Bridge — Framework for browser-based AI interaction.

When fully implemented with Playwright/Selenium, this can drive web AI
interfaces (DeepSeek Chat, ChatGPT web, Claude web, etc.) as an
alternative provider path.

Current status: FRAMEWORK — requires Playwright + real browser integration.
For now, use the "deepseek" API provider in OllamaClient for reliable
DeepSeek access.

Usage (when browser tools are fully implemented):
    bridge = WebAIBridge()
    reply = bridge.ask("Explain quantum computing", service="deepseek")
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from kai_agent.browser_tools import BrowserTools


@dataclass
class WebAIService:
    name: str
    url: str
    input_selector: str
    submit_selector: str
    response_selector: str
    response_wait: float = 5.0
    max_wait: float = 60.0
    pre_action: Callable | None = None


class WebAIBridge:
    """Bridge to web AI interfaces via browser automation."""

    SERVICES = {
        "deepseek": WebAIService(
            name="DeepSeek Chat",
            url="https://chat.deepseek.com",
            input_selector="textarea[placeholder*='message' i], textarea[class*='input'], #chat-input, [contenteditable='true']",
            submit_selector="button[type='submit'], button[class*='send'], .send-button, [aria-label*='send' i]",
            response_selector="[class*='message-content'], [class*='markdown-body'], [class*='chat-message'] div:last-child, .ds-markdown",
            response_wait=3.0,
            max_wait=45.0,
        ),
        "chatgpt": WebAIService(
            name="ChatGPT",
            url="https://chat.openai.com",
            input_selector="#prompt-textarea, textarea[placeholder*='message' i], [contenteditable='true'][data-placeholder]",
            submit_selector="button[data-testid='send-button'], button[class*='send']",
            response_selector="[data-testid='conversation-turn-2'] .markdown, [class*='group'] .prose",
            response_wait=4.0,
            max_wait=60.0,
        ),
        "claude": WebAIService(
            name="Claude",
            url="https://claude.ai",
            input_selector="[contenteditable='true'], textarea[placeholder*='Message' i]",
            submit_selector="button[aria-label*='Send' i], button[class*='send']",
            response_selector="[class*='font-claude-message'], [data-testid='user-message'] ~ div",
            response_wait=4.0,
            max_wait=60.0,
        ),
        "perplexity": WebAIService(
            name="Perplexity",
            url="https://www.perplexity.ai",
            input_selector="textarea[placeholder*='Ask' i], [contenteditable='true']",
            submit_selector="button[class*='submit'], button[aria-label*='submit' i]",
            response_selector="[class*='prose'], .answer",
            response_wait=5.0,
            max_wait=60.0,
        ),
    }

    def __init__(self, service: str = "deepseek", workspace: Path | None = None):
        self.service_name = service.lower()
        self.service = self.SERVICES.get(self.service_name)
        if not self.service:
            available = ", ".join(self.SERVICES.keys())
            raise ValueError(f"Unknown web AI service '{service}'. Available: {available}")
        self.workspace = workspace or Path(".")
        self._browser: BrowserTools | None = None
        self._last_response_text = ""

    def _get_browser(self) -> BrowserTools:
        if self._browser is None:
            self._browser = BrowserTools(workspace=self.workspace)
        return self._browser

    def ask(self, prompt: str, service: str | None = None) -> str:
        """Send a prompt to a web AI and return the text response."""
        if service and service != self.service_name:
            self.service_name = service.lower()
            self.service = self.SERVICES.get(self.service_name)
            if not self.service:
                available = ", ".join(self.SERVICES.keys())
                raise ValueError(f"Unknown web AI service '{service}'. Available: {available}")

        browser = self._get_browser()
        svc = self.service

        # Navigate to service
        result = json.loads(browser.browse(svc.url))
        if not result.get("ok"):
            raise RuntimeError(
                f"Web AI bridge not yet implemented. "
                f"Use the 'deepseek' API provider instead: /provider deepseek deepseek-chat\n"
                f"(Requires DEEPSEEK_API_KEY environment variable)"
            )

        # Future implementation would:
        # 1. Wait for page load
        # 2. Find input element and type prompt
        # 3. Click submit
        # 4. Poll for response text via DOM selectors
        # 5. Return extracted text

        raise RuntimeError(
            "Web AI bridge requires full Playwright browser integration.\n"
            "For now, use these API providers instead:\n"
            "  /provider ollama <model>     — local Ollama models\n"
            "  /provider deepseek <model>   — DeepSeek API (needs DEEPSEEK_API_KEY)\n"
            "  /provider hf <model>         — Hugging Face Inference API"
        )

    def close(self) -> None:
        self._browser = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def web_ai_chat(messages: list[dict], service: str = "deepseek", timeout: int = 60) -> str:
    """Convenience function: chat via web AI bridge from a messages list."""
    prompt_parts = []
    for msg in messages:
        role = str(msg.get("role", "user")).capitalize()
        content = str(msg.get("content", "")).strip()
        if content:
            prompt_parts.append(f"{role}: {content}")
    prompt = "\n\n".join(prompt_parts)

    with WebAIBridge(service=service) as bridge:
        return bridge.ask(prompt)

