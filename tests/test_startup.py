import subprocess
import sys
import time

# Test assistant startup (just init, then exit)
proc = subprocess.Popen(
    [sys.executable, "-m", "kai_agent.assistant", "--model", "sam860/dolphin3-llama3.2:3b"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait a few seconds for init, then send /exit
time.sleep(4)
proc.stdin.write("/exit\n")
proc.stdin.flush()

# Give it time to process
time.sleep(1)
proc.terminate()

stdout, stderr = proc.communicate(timeout=2)

with open("startup_test.txt", "w") as f:
    f.write(f"Return code: {proc.returncode}\n")
    f.write(f"STDOUT:\n{stdout}\n")
    f.write(f"STDERR:\n{stderr}\n")

print(f"Done. Return code: {proc.returncode}")

