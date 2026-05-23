"""TCP diagnostic — test bind, listen, and connect all in one script."""
import socket
import threading
import time
import sys

PORT = 5555

# Start server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    server.bind(("127.0.0.1", PORT))
    print(f"1. BIND OK — 127.0.0.1:{PORT}")
except Exception as e:
    print(f"1. BIND FAILED: {e}")
    sys.exit(1)

server.listen(5)
print(f"2. LISTEN OK")

accepted = threading.Event()
result = [None]

def accept_thread():
    try:
        conn, addr = server.accept()
        result[0] = (conn, addr)
        accepted.set()
    except Exception as e:
        result[0] = e
        accepted.set()

threading.Thread(target=accept_thread, daemon=True).start()
time.sleep(0.5)

# Try to connect
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.settimeout(5.0)
try:
    t0 = time.time()
    client.connect(("127.0.0.1", PORT))
    elapsed = time.time() - t0
    print(f"3. CONNECT OK — took {elapsed:.2f}s")
except Exception as e:
    elapsed = time.time() - t0
    print(f"3. CONNECT FAILED after {elapsed:.2f}s: {e}")

print(f"4. Server accepted: {accepted.is_set()}")
if accepted.is_set():
    conn, addr = result[0]
    print(f"5. Connection from: {addr}")
    try:
        data = b"HTTP/1.0 200 OK\r\nConnection: close\r\n\r\nHello"
        conn.sendall(data)
        print("6. Sent response OK")
    except Exception as e:
        print(f"6. Send failed: {e}")
    conn.close()

server.close()
client.close()
print("DONE")
