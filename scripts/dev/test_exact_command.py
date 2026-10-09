#!/usr/bin/env python3
"""Test the exact command FileSqueeze uses for PowerPoint conversion"""

import subprocess
import sys
from pathlib import Path

# Get the exact paths FileSqueeze uses
SCRIPTPATH = "D:/nyjc-edtech/filesqueeze/filesqueeze/bin/pptx2mp4.ps1"
test_file = "G:/Shared drives/compressor/upload/T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"
output_file = "G:/Shared drives/compressor/compressed/test_exact.mp4"

# Find PowerShell
powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

print(f"PowerShell: {powershell_path}")
print(f"Script: {SCRIPTPATH}")
print(f"Input: {test_file}")
print(f"Output: {output_file}")
print()

# Build the EXACT command FileSqueeze uses
cmd = [
    powershell_path,
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    SCRIPTPATH,
    "-Path",
    test_file,
    "-FilePath",
    output_file,
]

print(f'Command: {" ".join(cmd)}')
print()
print("Testing exact FileSqueeze command...")

try:
    result = subprocess.run(
        cmd,
        timeout=180,  # 3 minutes
        capture_output=True,
        text=True,
        check=False,  # We'll check return code ourselves
    )

    print(f"Return code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")

    if result.returncode == 0:
        print("[SUCCESS] Command completed successfully")
        if Path(output_file).exists():
            size = Path(output_file).stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"Output file created: {size_mb:.2f} MB")
    else:
        print("[FAILED] Command failed")
        sys.exit(1)

except subprocess.TimeoutExpired:
    print("[TIMEOUT] Command timed out after 3 minutes")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Exception: {e}")
    sys.exit(1)
