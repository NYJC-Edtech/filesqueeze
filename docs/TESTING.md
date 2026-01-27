# Safe Testing Guidelines for FileSqueeze

## ⚠️ CRITICAL WARNING

**PRODUCTION USER CONFIG LOCATION:**
- Windows: `C:\Users\<username>\.config\filesqueeze\config.toml`
- Linux/Mac: `~/.config/filesqueeze/config.toml`

**This file MUST NEVER be modified by tests.** The production config contains:
- Custom input/output directories (e.g., network drives)
- Auto-detected binary paths
- User-specific settings

If this file gets wiped or modified:
1. FileSqueeze service will stop working correctly
2. Custom directory mappings are lost
3. Binary detection settings are lost
4. User must manually restore the file

## Golden Rule
**NEVER modify production state during tests, even temporarily.**

## What NOT To Do

❌ **Dangerous: Moving/hiding user config files**
```python
# BAD: Risk of leaving system in broken state if test fails
import shutil
user_config = Path('~/.config/filesqueeze/config.toml')
shutil.move(user_config, backup_path)  # DANGEROUS!
try:
    # ... tests ...
finally:
    shutil.move(backup_path, user_config)  # May not run if test crashes!
```

**Why this is dangerous:**
- If test crashes or is interrupted, config stays moved
- Production FileSqueeze may be running and will fail
- User's custom settings disappear
- Hard to debug what went wrong

## SAFE Testing Patterns

### ✅ Pattern 1: Use Mock Config (Recommended)

```python
from filesqueeze.config import Config

# Pass test config directly - NO filesystem touched
test_config = Config({
    'directories': {
        'input': '/tmp/test/input',
        'output': '/tmp/test/output'
    },
    'processing': {
        'timeout_seconds': 100
    }
})

# Test behavior with isolated config
assert test_config.get('processing.timeout_seconds') == 100
```

**Benefits:**
- Zero risk to production state
- Tests run in complete isolation
- Fast - no file I/O
- Can test edge cases easily

### ✅ Pattern 2: Test with Actual Config (Read-Only)

```python
from filesqueeze.config import Config

# Verify config loading works (READ-ONLY)
config = Config()

# Verify defaults are loaded correctly
assert config.get('processing.pdf_timeout_seconds') == 300
assert config.get('processing.ocr_timeout_seconds') == 300

# Verify user config overrides work
user_input = config.get('directories.input')
# Just read, never write!
```

**Benefits:**
- Tests real config loading
- Zero risk (read-only)
- Verifies cascade works

### ✅ Pattern 3: Use Temporary Directories for File Operations

```python
import tempfile
from pathlib import Path

# Create isolated temp directory
with tempfile.TemporaryDirectory() as tmpdir:
    test_config_path = Path(tmpdir) / 'config.toml'
    test_config_path.write_text('[directories]\ninput = "/tmp/test"\n')

    # Load from test location
    config = Config(test_config_path)
    assert config.get('directories.input') == '/tmp/test'

# Temp dir auto-cleanup - zero risk to production
```

**Benefits:**
- Safe file operations in isolated space
- Auto-cleanup guaranteed
- No risk to user config

## Testing Checklist

Before running any test that touches config:

- [ ] Am I modifying `~/.config/filesqueeze/config.toml`? → **STOP**
- [ ] Am I modifying project `filesqueeze.toml`? → **Use temp dir instead**
- [ ] Am I modifying `default.toml`? → **Use temp dir instead**
- [ ] Can I use a mock dict instead? → **DO THAT**
- [ ] Can I use tempfile.TemporaryDirectory? → **DO THAT**

## Safe Test Examples

### Testing Config Loading
```python
# SAFE: Read-only verification
config = Config()
assert config.get('processing.pdf_timeout_seconds') == 300
assert config.get('processing.ocr_timeout_seconds') == 300
```

### Testing Config with Custom Values
```python
# SAFE: Use mock dict
config = Config({
    'processing': {
        'pdf_timeout_seconds': 999
    }
})
assert config.get('processing.pdf_timeout_seconds') == 999
```

### Testing Config from File
```python
# SAFE: Use temp directory
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    config_path = Path(tmpdir) / 'test.toml'
    config_path.write_text('[processing]\npdf_timeout_seconds = 999\n')

    config = Config(config_path)
    assert config.get('processing.pdf_timeout_seconds') == 999
```

## Production Safety

If you suspect tests may have touched production:

1. **Check user config exists:**
   ```python
   from pathlib import Path
   user_config = Path('~/.config/filesqueeze/config.toml').expanduser()
   print(f'Config exists: {user_config.exists()}')
   ```

2. **Check FileSqueeze service status:**
   ```bash
   filesqueeze service status
   ```

3. **If missing, restore from backup or reinstall**

## Summary

- ✅ Use mock configs for testing
- ✅ Use read-only checks for verification
- ✅ Use temp directories for file operations
- ❌ NEVER touch user config files
- ❌ NEVER move/hide production files
- ❌ NEVER assume cleanup will run

**Tests should be safe to run on a production system.**
