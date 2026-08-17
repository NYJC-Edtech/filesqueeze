#!/usr/bin/env python3
"""Test Google Drive detection functionality"""

from filesqueeze.utils.google_drive import is_google_drive_path

# Test cases for Google Drive detection
test_cases = [
    # (path, expected_result, description)
    (r"G:\Shared drives\compressor\upload\test.pptx", True, "Google Drive Shared Drive"),
    (r"G:\Shared Drives\compressor\upload\test.pptx", True, "Google Drive Shared Drive (capitalized)"),
    (r"C:\Users\Test\My Drive\Documents\test.pdf", True, "Google Drive My Drive"),
    (r"C:\Users\Test\Team Drives\project\file.mp4", True, "Google Drive Team Drives"),
    (r"\\google\drive\mount\test.txt", True, "Google Drive UNC path"),
    (r"C:\Users\Test\Documents\local\file.pdf", False, "Local directory"),
    (r"D:\Projects\filesqueeze\test.mp4", False, "Local project directory"),
    (r"/home/user/documents/file.pdf", False, "Linux local path"),
]

print("Testing Google Drive detection...")
print("=" * 50)

passed = 0
failed = 0

for path, expected, description in test_cases:
    result = is_google_drive_path(path)
    status = "[OK]" if result == expected else "[FAIL]"

    if result == expected:
        passed += 1
    else:
        failed += 1

    print(f"{status} {description}")
    print(f"  Path: {path}")
    print(f"  Expected: {expected}, Got: {result}")
    print()

print("=" * 50)
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("All tests passed!")
else:
    print(f"WARNING: {failed} test(s) failed")
