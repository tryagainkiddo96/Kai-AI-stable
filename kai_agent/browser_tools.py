"""
Browser tools — Playwright-based web automation with Chimera stealth + AnonymityStack.
"""
import json
import random
import time
from pathlib import Path


class BrowserTools:
    def __init__(self, workspace, chimera=None, anonymity=None):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._context = None
        self._page = None
        self._screenshots_dir = self.workspace / "screenshots"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._downloads_dir = self.workspace / "downloads"
        self._downloads_dir.mkdir(parents=True, exist_ok=True)

        # Inject stealth controllers
        self.chimera = chimera
        self.anonymity = anonymity

    def _get_stealth_config(self):
        """Generate stealth config from Chimera + AnonymityStack."""
        config = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 720},
            "proxy": None,
        }

        if self.chimera:
            fp = self.chimera.current_fingerprint
            if fp.get("user_agent"):
                config["user_agent"] = fp["user_agent"]

        if self.anonymity:
            fp = self.anonymity.generate_fingerprint()
            config["user_agent"] = fp["user_agent"]

            width = random.choice([1280, 1366, 1440, 1536, 1920])
            height = random.choice([720, 768, 900, 864, 1080])
            config["viewport"] = {"width": width, "height": height}

            if self.anonymity.current_proxy:
                proxy = self.anonymity.current_proxy
                if "http" in proxy:
                    config["proxy"] = {"server": proxy["http"]}

        return config

    def _ensure_page(self):
        from playwright.sync_api import sync_playwright
        if self._page is None:
            stealth = self._get_stealth_config()
            pw = sync_playwright().start()
            self._browser = pw.chromium.launch(headless=False)

            context_kwargs = {
                "viewport": stealth["viewport"],
                "accept_downloads": True,
                "user_agent": stealth["user_agent"],
            }
            if stealth["proxy"]:
                context_kwargs["proxy"] = stealth["proxy"]

            self._context = self._browser.new_context(**context_kwargs)

            # Inject anti-detection scripts
            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                window.chrome = { runtime: {} };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) =>
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters);
                (function () {
                    const originalFillText = CanvasRenderingContext2D.prototype.fillText;
                    CanvasRenderingContext2D.prototype.fillText = function () {
                        return originalFillText.apply(this, arguments);
                    };
                })();
            """)

            self._page = self._context.new_page()
            self._page.set_default_timeout(15000)
        return self._page

    def _close(self):
        if self._browser:
            self._browser.close()
        self._browser = None
        self._context = None
        self._page = None

    def _apply_human_timing(self):
        if self.anonymity:
            self.anonymity.human_delay("browse")
        else:
            time.sleep(random.uniform(1.0, 3.0))

    def browse(self, url):
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            self._apply_human_timing()
            page = self._ensure_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            result = {"ok": True, "url": page.url, "title": page.title()}
            if self.anonymity:
                result["proxied"] = bool(self.anonymity.current_proxy)
            return json.dumps(result)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def search(self, query, site=""):
        try:
            if site:
                query = f"{query} site:{site}"
            self._apply_human_timing()
            page = self._ensure_page()
            page.goto(f"https://www.google.com/search?q={query}", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector("#search", timeout=10000)
            results = []
            for el in page.query_selector_all("#search .g"):
                title_el = el.query_selector("h3")
                link_el = el.query_selector("a")
                if title_el and link_el:
                    results.append({"title": title_el.inner_text(), "url": link_el.get_attribute("href")})
            return json.dumps({"ok": True, "results": results[:10], "query": query, "site": site})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def get_page_content(self):
        try:
            page = self._ensure_page()
            text = page.inner_text("body")
            return json.dumps({"ok": True, "url": page.url, "title": page.title(), "text": text[:3000]})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def get_page_links(self):
        try:
            page = self._ensure_page()
            links = [{"text": el.inner_text().strip()[:100], "url": el.get_attribute("href")} for el in page.query_selector_all("a[href]")]
            return json.dumps({"ok": True, "links": links[:50], "url": page.url})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def click_link(self, text):
        try:
            page = self._ensure_page()
            self._apply_human_timing()
            page.get_by_role("link", name=text, exact=False).click()
            page.wait_for_load_state("domcontentloaded")
            return json.dumps({"ok": True, "url": page.url, "title": page.title()})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def find_forms(self):
        try:
            page = self._ensure_page()
            forms = []
            for i, form in enumerate(page.query_selector_all("form")):
                inputs = [{"tag": el.evaluate("e => e.tagName"), "name": el.get_attribute("name"), "type": el.get_attribute("type"), "id": el.get_attribute("id")} for el in form.query_selector_all("input, textarea, select")]
                forms.append({"index": i, "action": form.get_attribute("action"), "inputs": inputs})
            return json.dumps({"ok": True, "forms": forms, "url": page.url})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def fill_form(self, data, form_index=0):
        try:
            page = self._ensure_page()
            forms = page.query_selector_all("form")
            if form_index >= len(forms):
                return json.dumps({"ok": False, "error": f"Form index {form_index} out of range"})
            form = forms[form_index]
            for inputs in form.query_selector_all("input, textarea"):
                name = inputs.get_attribute("name")
                inp_type = inputs.get_attribute("type") or "text"
                if name and name in data and inp_type not in ("submit", "button", "hidden"):
                    if self.anonymity:
                        self.anonymity.human_delay("type")
                    inputs.fill(str(data[name]))
            return json.dumps({"ok": True, "message": f"Filled {len(data)} fields in form {form_index}"})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def screenshot(self, filename=None):
        try:
            page = self._ensure_page()
            if filename is None:
                filename = f"screenshot_{int(time.time())}.png"
            path = str(self._screenshots_dir / filename)
            page.screenshot(path=path, full_page=False)
            return json.dumps({"ok": True, "path": path, "url": page.url})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def download_file(self, url, filename=None):
        try:
            page = self._ensure_page()
            with page.expect_download(timeout=30000) as dl_info:
                page.goto(url, wait_until="domcontentloaded")
            dl = dl_info.value
            dest = str(self._downloads_dir / (filename or dl.suggested_filename))
            dl.save_as(dest)
            return json.dumps({"ok": True, "path": dest})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    def close(self):
        try:
            self._close()
            return json.dumps({"ok": True, "message": "Browser closed"})
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})
