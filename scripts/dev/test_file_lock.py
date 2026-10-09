#!/usr/bin/env python3
"""Test if the PowerPoint file is locked by Google Drive"""

import os
import sys
from pathlib import Path

pptx_file = r"G:\Shared drives\compressor\upload\T3W7 Tut2_ Chap 9 Sec 3 Q5_recording.pptx"

print(f"Testing file access: {pptx_file}")
print("=" * 50)

try:
    path = Path(pptx_file)
    if not path.exists():
        print(f"[ERROR] File does not exist: {pptx_file}")
        sys.exit(1)

    print(f"[OK] File exists: {pptx_file}")
    print(f"  Size: {path.stat().st_size:,} bytes")

    # Test if file can be opened exclusively
    print("Testing exclusive file access...")
    try:
        # Try to open file in exclusive mode
        fd = os.open(pptx_file, os.O_RDONLY | os.O_EXCL)
        print("[OK] File is NOT locked (exclusive access succeeded)")
        os.close(fd)
    except OSError as e:
        print(f"[LOCKED] File is locked: {e}")
        print("  This usually means Google Drive is syncing the file")

    # Try to open file normally
    try:
        with open(pptx_file, "rb") as f:
            header = f.read(8)
            print(f"[OK] File can be opened normally (header: {header.hex()})")
    except Exception as e:
        print(f"[ERROR] Cannot open file: {e}")

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    sys.exit(1)
