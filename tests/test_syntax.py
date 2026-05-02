# Test the syntax fix
target = "test_target"
file_path = "test_file.py"

# This should work
cmd = ["powershell", "-NoProfile", "-Command", f"Start-Process powershell -ArgumentList '-NoExit','-Command','cd \"{target}\"; python \"{file_path}\"'"]
print("Command created successfully:", cmd)