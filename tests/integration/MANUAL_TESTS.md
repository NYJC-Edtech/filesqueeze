# Manual Test Procedures

These tests require manual execution or full system installation.

## Process Cleanup Test

**Objective:** Verify uninstallation stops all FileSqueeze processes.

**Steps:**
1. Install FileSqueeze: `.\install.ps1`
2. Start the service: `filesqueeze service run`
3. Verify it's running:
   ```powershell
   tasklist | findstr filesqueeze
   ```
4. In a new PowerShell window, run uninstall: `.\uninstall.ps1`
5. Verify all processes are gone:
   ```powershell
   tasklist | findstr filesqueeze
   ```
   (Should return nothing)

**Expected Result:** All FileSqueeze processes are stopped during uninstall.

**Automated Test Status:** Code-level test verifies uninstall script has the right logic (`Stop-Process`/`taskkill` commands), but full end-to-end requires manual testing.

## App Identity Persistence Test

**Objective:** Verify Windows remembers FileSqueeze across restarts.

**Steps:**
1. Install FileSqueeze
2. Start the service: `filesqueeze service run`
3. Locate the FileSqueeze tray icon in system tray (may need to click "^" to show hidden icons)
4. Right-click the tray icon
5. Select "Show Notification Area Icons" or similar
6. Set FileSqueeze to "Show icon and notifications"
7. Stop FileSqueeze (right-click → Quit)
8. **Restart your computer**
9. Start FileSqueeze again: `filesqueeze service run`
10. Verify the tray icon is still set to "Show icon and notifications"

**Expected Result:** Windows remembers FileSqueeze's display settings across restart.

**Note:** This tests the AppUserModelID implementation. If it fails, check the logs for:
```
Successfully set AppUserModelID: com.filesqueeze.app
```

## Console Window Test

**Objective:** Verify service mode runs without console window.

**Steps:**
1. Start FileSqueeze: `filesqueeze service run`
2. Check that no console window appears (should only see tray icon)
3. Verify in Task Manager that `filesqueeze.exe` is running
4. Double-click the tray icon to open status window
5. Verify status window opens, but no additional console windows appear

**Expected Result:** Service runs silently with only tray icon and status window visible.

## Status Window Singleton Test

**Objective:** Verify only one status window can be open.

**Automated Test:** ✅ `test_tray_service_enforces_singleton_window` passes

**Manual Verification (Optional):**
1. Start FileSqueeze service
2. Double-click tray icon → Status window opens
3. Double-click tray icon again → No new window opens
4. Close status window
5. Double-click tray icon → New window opens

**Expected Result:** Only one status window exists at any time.
