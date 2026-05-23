"""Quick test — run this to verify Flask and browser work."""
from flask import Flask
import threading, time, webbrowser

app = Flask(__name__)

@app.route("/")
def index():
    return "Kai test OK"

PORT = 5555
print(f"Starting test server on http://localhost:{PORT}")
print("Open that in your browser. You should see 'Kai test OK'")

def _open():
    time.sleep(1)
    webbrowser.open(f"http://localhost:{PORT}")

threading.Thread(target=_open, daemon=True).start()
app.run(host="0.0.0.0", port=PORT, debug=False)
