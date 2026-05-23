"""Ultra-minimal test — just a single plain response."""
import socket
import threading
import time
import webbrowser

def handle_client(conn):
    conn.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 21\r\n\r\nKai server works!\r\n")
    conn.close()

def run():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 5555))
    s.listen(5)
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

port = 5555
print(f"Server on http://127.0.0.1:{port}")
print(f"Server on http://localhost:{port}")
threading.Thread(target=run, daemon=True).start()
threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://127.0.0.1:{port}")), daemon=True).start()
input("Press Enter to stop...")
