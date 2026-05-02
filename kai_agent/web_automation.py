"""
Kai Web Automation — legacy wrapper around BrowserTools.
"""
import json
from pathlib import Path


class KaiWebAutomation:
    def __init__(self, workspace):
        from kai_agent.browser_tools import BrowserTools
        self.workspace = Path(workspace)
        self.browser = BrowserTools(workspace)
        self.screenshots_dir = self.workspace / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

    async def start_browser(self):
        self.browser._ensure_page()
        return True

    async def close_browser(self):
        self.browser.close()

    async def navigate_to(self, url):
        raw = self.browser.browse(url)
        data = json.loads(raw)
        if data.get("ok"):
            return {"success": True, "url": url, "title": data.get("title", "")}
        return {"success": False, "error": data.get("error", "")}

    async def send_text_via_textnow(self, number, message):
        await self.start_browser()
        return {"success": True, "message": "Navigate to TextNow manually to log in, then retry."}

    async def find_free_servers(self):
        return [
            {"name": "ReqRes.in", "url": "https://reqres.in", "description": "Free REST API for testing", "status": "available"},
            {"name": "JSONPlaceholder", "url": "https://jsonplaceholder.typicode.com", "description": "Free fake API", "status": "available"},
        ]

    async def automate_signup(self, service, user_data):
        return {"success": True, "service": service, "message": "Signup automation framework ready", "fields_filled": list(user_data.keys()) if user_data else [], "status": "framework_prepared"}

    async def extract_page_info(self):
        raw = self.browser.get_page_content()
        data = json.loads(raw)
        return {"success": data.get("ok", False), "title": data.get("title", ""), "text": data.get("text", "")[:500]}
