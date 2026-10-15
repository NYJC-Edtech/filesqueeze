# Installation Script Principles

This document outlines the key principles and best practices learned from developing FileSqueeze installation scripts. These principles should guide development of installation scripts for both Windows and Unix-like systems.

## Core Principles

### 1. PATH Refresh Awareness

**Problem**: When installing Python packages via pip, command-line tools are installed but the current shell session doesn't see the updated PATH environment variable.

**Solutions**:
- **Primary**: Refresh PATH environment variable in the current session after package installation
- **Fallback**: Use `python -m package` syntax instead of direct `package` commands
- **Alternative**: Use absolute paths to executables when available

**Example (PowerShell)**:
```powershell
# After pip install, refresh PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + 
             [System.Environment]::GetEnvironmentVariable("Path","User")

# Then provide fallback
try {
    filesqueeze service install
} catch {
    python -m filesqueeze service install
}
```

**Example (Bash)**:
```bash
# After pip install, refresh PATH
export PATH="$HOME/.local/bin:$PATH"

# Always use module syntax for reliability
python -m filesqueeze service install
```

### 2. Robust Error Handling

**Problem**: Silent failures in installation scripts make debugging extremely difficult for users.

**Solutions**:
- **Never silently catch errors** without logging what went wrong
- **Always show the exact command** that failed
- **Provide clear error messages** with recovery instructions
- **Log both the error and context** (what was being attempted)

**Bad Practice**:
```powershell
try {
    Install-Something
} catch {
    Write-Host "Installation failed. Try manually."
}
```

**Good Practice**:
```powershell
try {
    Write-Host "Running: $cmd" -ForegroundColor Gray
    $output = Invoke-Expression $cmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE. Output: $output"
    }
} catch {
    Write-Host "Auto-start installation failed:" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host "  You can enable auto-start later by running: filesqueeze service install" -ForegroundColor Yellow
}
```

### 3. Graceful Degradation with Fallbacks

**Problem**: Installation environments vary wildly; what works in one environment may fail in another.

**Solutions**:
- **Try multiple methods** in order of preference
- **Provide clear fallbacks** when primary method fails
- **Document manual steps** if all automated methods fail

**Example**:
```powershell
# Try Poetry first (project standard)
if (Get-Command poetry -ErrorAction SilentlyContinue) {
    poetry build
} else {
    # Fall back to standard Python build
    python -m build
}
```

### 4. Build Tool Compatibility

**Problem**: Different projects use different build systems (Poetry, setuptools, flit). Installation scripts must handle multiple scenarios.

**Solutions**:
- **Detect available build tools** before attempting to build
- **Provide fallbacks** for different build systems
- **Never use invalid commands** (e.g., `pip build` doesn't exist)

**Build Tool Priority**:
1. **Poetry** (if pyproject.toml uses poetry-core)
2. **Python build module** (`python -m build`)
3. **Direct setuptools** (for legacy projects)

### 5. Configuration File Compatibility

**Problem**: Configuration files may use different formats or section names across versions.

**Solutions**:
- **Support multiple config patterns** (root-level, sectioned)
- **Use robust pattern matching** when parsing configs
- **Provide defaults** when config values aren't found

**Example**:
```powershell
# Check for [directories] section first
if ($configContent -match '\[directories\]([\s\S]*?)\[.*?\]') {
    $directoriesSection = $matches[1]
    if ($directoriesSection -match 'input\s*=\s*"([^"]+)"') {
        $inputDir = $matches[1]
    }
}
# Fallback to root-level or [service] section
elseif ($configContent -match 'input\s*=\s*"([^"]+)"') {
    $inputDir = $matches[1]
}
```

### 6. Verbose Logging with Debug Information

**Problem**: When installations fail, users need to provide enough context for debugging.

**Solutions**:
- **Log the exact commands** being executed
- **Show command output** (both stdout and stderr)
- **Include exit codes** when commands fail
- **Provide environment context** (Python version, OS, etc.)

### 7. Preserve User Settings Across Reinstalls

**Problem**: The uninstaller removes the auto-start Startup shortcut(s) unconditionally, so a
`-Force` reinstall that never re-offers auto-start silently drops start-on-boot. The loss is
invisible until the next reboot — production ran three days without auto-start after a routine
reinstall before anyone noticed (2026-10).

**Solutions**:
- **Capture the pre-install state** (which Startup shortcuts exist) before anything is removed
- **Re-offer the SAME scope** on reinstall: declining the prompt may be an informed choice,
  never a silent loss, and a user-level install must not be upgraded to system-wide by accident
- **Leave surviving shortcuts alone**: removing the all-users shortcut without admin fails, so
  a shortcut can still be there when the prompt runs — reinstalling over it exits with an error
- **Make declines explicit**: when the user declines a restore, say that auto-start stays
  disabled and print the exact command to re-enable it later
- **Detect the failure mode**: `filesqueeze doctor` warns when auto-start is missing or points
  at a missing script, so a lost shortcut is visible without waiting for a reboot

## Platform-Specific Considerations

### Windows (PowerShell)

- **Use `Invoke-Expression`** for dynamic command execution
- **Check `$LASTEXITCODE`** for command success/failure
- **Handle Windows paths** with backslashes properly
- **Create shortcuts** for Start Menu and Startup
- **Handle process termination** for running services

### Unix-like (Bash)

- **Always use `set -e`** for error handling
- **Use `python -m package`** instead of relying on PATH
- **Create systemd services** for auto-start
- **Handle shebang lines** properly for scripts
- **Use absolute paths** in systemd service files

## Testing Checklist

Before releasing installation scripts, test:

- [ ] Fresh installation on clean system
- [ ] Reinstallation with `--force` flag
- [ ] Installation when build tools are missing
- [ ] Installation when dependencies are already installed
- [ ] PATH refresh in current shell session
- [ ] Configuration file generation
- [ ] Auto-start/shortcut creation
- [ ] Auto-start survives a `-Force` reinstall (re-offered with the same scope)
- [ ] Uninstallation removes all components
- [ ] Error messages are clear and actionable

## Common Pitfalls

1. **Assuming commands are available**: Always check before using
2. **Silent failures**: Never catch errors without logging
3. **PATH timing issues**: Refresh PATH after package installations
4. **Hard-coded paths**: Use environment variables and config files
5. **Insufficient error context**: Always show what failed and why
6. **Functions used before defined (PowerShell)**: Scripts run top-to-bottom; a helper called
   above its definition throws, and inside a `try/catch` the throw is swallowed — the
   service-stop block once stopped nothing this way. Define helpers before first use.
7. **Uninstaller removes settings the installer doesn't restore**: Any state the uninstaller
   clears (Startup shortcuts, config) must be captured first and re-offered by the installer

## Maintenance

Installation scripts should be reviewed and updated:
- When dependency versions change
- When new Python versions are released
- When configuration formats change
- When user-reported issues indicate problems
- When adding new installation methods

## Resources

- [PowerShell Error Handling](https://docs.microsoft.com/en-us/powershell/scripting/learn/deep-dives/everything-about-exceptions)
- [Bash Best Practices](https://github.com/alexharv074/bash-best-practices)
- [Python Packaging Guide](https://packaging.python.org/en/latest/guides/)
- [Cross-platform Python Scripts](https://github.com/pradyunsg/furo/blob/main/docs/conf.py)