"""
Browser tools stub - Playwright disabled to avoid Node.js dependency issues.
"""

class BrowserTools:
    def __init__(self, workspace):
        self.workspace = workspace
    
    def browse(self, url):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def search_web_browser(self, query, site=""):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def get_page_content(self):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def get_links(self):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def click_link(self, text):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def fill_form(self, data, form_index=0):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def find_forms(self):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def download(self, url=None, filename=None):
        return '{"ok": false, "error": "Browser tools disabled"}'
    
    def screenshot(self, filename="screenshot.png"):
        return '{"ok": false, "error": "Browser tools disabled"}'
