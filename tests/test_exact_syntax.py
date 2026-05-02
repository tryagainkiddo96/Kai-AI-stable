# Test the exact syntax we need
target = "test_path"
file_path = "test_file.py"

# This should work without syntax errors
cmd = ["powershell", "-NoProfile", "-Command", f"Start-Process powershell -ArgumentList '-NoExit','-Command','cd \"{target}\"; python \"{file_path}\"'"]
print("Syntax test passed!")
print("Command:", cmd)