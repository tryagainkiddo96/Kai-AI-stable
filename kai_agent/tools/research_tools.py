"""Research Tools — web search via Tavily."""
from __future__ import annotations

import json

from kai_agent.tavily_client import TavilyClient


class ResearchTools:
    def __init__(self) -> None:
        self.tavily = TavilyClient()

    def search_web(self, query: str, max_results: int = 5) -> str:
        return json.dumps(self.tavily.search(query=query, max_results=max_results), indent=2)
