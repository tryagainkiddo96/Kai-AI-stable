import subprocess
import sys

# Test launching kai_agent.assistant with --help
result = subprocess.run(
    [sys.executable, "-m", "kai_agent.assistant", "--help"],
    capture_output=True, text=True, timeout=10
)

with open("launch_test.txt", "w") as f:
    f.write(f"Return code: {result.returncode}\n")
    f.write(f"STDOUT:\n{result.stdout}\n")
    f.write(f"STDERR:\n{result.stderr}\n")

print(f"Done. Return code: {result.returncode}")

