#!/usr/bin/env python3
"""Test PowerPoint file creation with timing like the actual process"""

import os
import sys
import time
from pathlib import Path

pptx_file = r"G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"
test_output = r"G:\Shared drives\compressor\compressed\test_locking.mp4"

print("Simulating PowerPoint file operations...")
print("=" * 50)

try:
    # Test 1: Can we copy the file (simulate file read)
    print("Test 1: Copying file to simulate PowerPoint read...")
    start = time.time()

    try:
        # Try to copy file like PowerPoint would read it
        import shutil

        temp_copy = test_output.replace(".mp4", "_temp.pptx")
        shutil.copy2(pptx_file, temp_copy)
        elapsed = time.time() - start
        print(f"[OK] File copied successfully ({elapsed:.2f}s)")
        Path(temp_copy).unlink()
    except Exception as e:
        print(f"[FAIL] Could not copy file: {e}")

    # Test 2: Can we create a file in the output directory
    print("Test 2: Creating file in output directory...")
    start = time.time()

    try:
        with open(test_output, "wb") as f:
            f.write(b"Test content")
        elapsed = time.time() - start
        print(f"[OK] File created successfully ({elapsed:.2f}s)")
        size = Path(test_output).stat().st_size
        print(f"  Size: {size} bytes")
        Path(test_output).unlink()
    except Exception as e:
        print(f"[FAIL] Could not create file: {e}")

    # Test 3: Check Google Drive sync status
    print("Test 3: Checking for Google Drive sync processes...")
    try:
        result = os.popen('tasklist /FI "IMAGENAME eq GoogleDriveSync.exe" 2>NUL').read()
        if result.strip():
            print("[INFO] Google Drive sync process is running")
            # Try to get more details
            processes = os.popen("wmic process where \"name like '%GoogleDrive%'\" get ProcessId,CommandLine 2>NUL").read()
            print("  Running Google Drive processes found")
        else:
            print("[OK] No Google Drive sync process detected")
    except:
        print("[WARN] Could not check for Google Drive processes")

    print("\n" + "=" * 50)
    print("Summary: File operations work, but PowerPoint CreateVideo")
    print("         might fail due to internal file locking or sync conflicts.")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
