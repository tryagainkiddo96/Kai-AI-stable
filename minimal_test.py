"""Minimal HTTP test — no Flask, no dependencies."""
import http.server
import socketserver
import threading
import time
import webbrowser

PORT = 5555

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"Server works on port {PORT}!".encode())

httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)

print("=" * 50)
print(f"  >>>  http://127.0.0.1:{PORT}  <<<")
print("=" * 50)
print()
print("  Open this in your browser NOW.")
print()

# Auto-open
threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://127.0.0.1:{PORT}")), daemon=True).start()

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nStopped.")
    httpd.shutdown()
