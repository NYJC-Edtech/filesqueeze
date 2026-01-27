# Cross-Platform Path Handling Design

## Golden Rule

**Use `pathlib.Path` objects internally. Convert to strings only at boundaries.**

## Problem Statement

FileSqueeze runs on Windows and Linux. Path handling must:
1. Work correctly on both platforms
2. Handle mixed environments (e.g., Linux accessing Windows shares via SMB)
3. Store paths portably in configuration files
4. Pass paths correctly to external tools (FFmpeg, Ghostscript, Tesseract)

## Current Issues

### Issue 1: Mixed Slashes in Display
```
Input dir: C:\Users\ICT Department/FileSqueeze/upload
```
This happens because:
- Config stores expanded strings (backslashes on Windows)
- Some code uses forward slashes (hardcoded or from TOML)
- Display mixes both

### Issue 2: String vs Path Object Confusion
```python
config.get('directories.input')  # Returns string (backslashes)
config.input_dir                  # Returns Path object (platform-aware)
```
Inconsistent return types confuse developers.

### Issue 3: TOML Portability
```toml
input = "G:/Shared drives/compressor/upload"  # Forward slashes
```
Forward slashes work on Windows but look unfamiliar to users.

## Design Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Config Layer                              │
│  - Stores paths as STRINGS in _config dict                   │
│  - Paths expanded at load time (os.path.expanduser)        │
│  - @property methods return Path objects                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Application Layer                            │
│  - All internal code uses Path objects                      │
│  - Path operations: /, .parent, .name, .stem, .suffix      │
│  - Accepts str | Path, converts to Path immediately         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Boundary Layer                             │
│  Subprocess: str(path)          → Platform-native separators│
│  TOML/JSON:  path.as_posix()    → Forward slashes (portable)│
│  Logging:    str(path)          → Platform-native           │
│  User display: str(path)        → Platform-native           │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Rules

#### 1. Internal Code (Application Layer)

```python
from pathlib import Path
from typing import Union

def process_file(filepath: Union[str, Path]) -> None:
    """Always convert to Path immediately."""
    path = Path(filepath) if isinstance(filepath, str) else filepath

    # Use Path operations
    parent = path.parent          # Parent directory
    stem = path.stem              # Filename without extension
    suffix = path.suffix          # File extension

    # Path joining is platform-aware
    output = path.parent / f"{stem}_compressed{suffix}"
```

**Benefits:**
- ✅ Platform-aware separators
- ✅ Clean, readable code
- ✅ No manual slash handling
- ✅ Works on Windows, Linux, macOS

#### 2. Config Properties

```python
class Config:
    @property
    def input_dir(self) -> Path:
        """Get input directory as Path object."""
        path_str = self.get('directories.input')
        return Path(path_str)

    @property
    def output_dir(self) -> Path:
        """Get output directory as Path object."""
        path_str = self.get('directories.output')
        return Path(path_str)

    @property
    def log_file(self) -> Path:
        """Get log file path as Path object."""
        path_str = self.get('logging.file')
        return Path(path_str)
```

**Benefits:**
- ✅ Consistent return type (Path)
- ✅ Auto-completion in IDEs
- ✅ Type checking with mypy
- ✅ No confusion about string vs Path

#### 3. Subprocess Calls (Boundary Layer)

```python
import subprocess
from pathlib import Path

def run_ffmpeg(input_file: Path, output_file: Path) -> None:
    """Convert to platform-native string for subprocess."""
    cmd = [
        'ffmpeg',
        '-i', str(input_file),      # Platform-native separators
        '-o', str(output_file)      # Platform-native separators
    ]
    subprocess.run(cmd)
```

**Why `str()` not `as_posix()`:**
- Windows tools understand both `\` and `/`
- `str()` uses platform-native format (familiar to users)
- `os.fspath()` also works (same as `str()` for Path)

#### 4. TOML/JSON Storage (Serialization)

```python
def save_config(config: Config, path: Path) -> None:
    """Save config with portable paths."""
    data = {
        'directories': {
            'input': config.input_dir.as_posix(),    # Forward slashes
            'output': config.output_dir.as_posix()   # Portable
        }
    }
    with open(path, 'w') as f:
        toml.dump(data, f)
```

**Why `as_posix()`:**
- ✅ Forward slashes work on ALL platforms (including Windows)
- ✅ TOML files are portable across systems
- ✅ Git diffs are cleaner (no escape sequences)
- ✅ Standard practice for config files

#### 5. Logging and Display

```python
def log_processing(file: Path) -> None:
    """Log file processing."""
    logger.info(f"Processing: {file}")
    # str() gives platform-native path (familiar to users)

    # For cross-platform logs, use as_posix()
    logger.debug(f"Processing (portable): {file.as_posix()}")
```

**Guidelines:**
- User-facing: `str(path)` - familiar format
- Debug logs: `path.as_posix()` - portable
- Error messages: `str(path)` - user can copy-paste

### Path Conversion Cheat Sheet

| Context | Method | Example Output | Use Case |
|---------|--------|----------------|----------|
| Internal operations | Keep as `Path` | `Path('C:/Users/test')` | All code |
| Subprocess (Windows) | `str(path)` | `C:\Users\test` | External tools |
| Subprocess (Linux) | `str(path)` | `/home/user/test` | External tools |
| TOML storage | `path.as_posix()` | `C:/Users/test` | Config files |
| JSON storage | `path.as_posix()` | `C:/Users/test` | API responses |
| User display | `str(path)` | Platform-native | GUI, CLI |
| Logging | `str(path)` or `as_posix()` | Depends | Logs |
| Network paths (Windows) | `str(path)` | `\\server\share` | UNC paths |

### Special Cases

#### Windows UNC Paths (Network Shares)

```python
# UNC paths on Windows
unc_path = Path(r'\\server\share\file.txt')

# str() preserves UNC format
str(unc_path)  # \\server\share\file.txt

# as_posix() converts to forward slashes
unc_path.as_posix()  # //server/share/file.txt
```

**Rule:** Use `str()` for Windows UNC paths to maintain compatibility.

#### Environment Variables

```python
# Config expands environment variables at load time
input = "%USERPROFILE%/FileSqueeze/input"
# Expands to: C:\Users\Name\FileSqueeze\input

# Use in code
config = Config()
input_path = config.input_dir  # Already expanded Path object
```

**Benefits:**
- ✅ One-time expansion at config load
- ✅ No need to remember expandvars() in code
- ✅ Path objects are ready to use

### Migration Path

#### Phase 1: Add Path Properties (Non-Breaking)

```python
# Add to config.py
@property
def log_file(self) -> Path:
    """Get log file path as Path object."""
    return Path(self.get('logging.file'))

@property
def ffmpeg_path(self) -> Path:
    """Get FFmpeg path as Path object."""
    path_str = self.get('ffmpeg.path', '')
    return Path(path_str) if path_str else Path('ffmpeg')
```

#### Phase 2: Update Code Gradually

```python
# Before (string handling)
input_path = config.get('directories.input')
file_path = os.path.join(input_path, filename)

# After (Path handling)
file_path = config.input_dir / filename
```

#### Phase 3: Type Annotations

```python
from pathlib import Path
from typing import Union

def process_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path]
) -> None:
    """Process a file."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    # ... rest of code
```

## Testing

### Unit Tests

```python
import pytest
from pathlib import Path
from filesqueeze.config import Config

def test_config_returns_path_objects():
    """Config properties return Path objects."""
    config = Config({'directories': {'input': '/tmp/test'}})

    assert isinstance(config.input_dir, Path)
    assert config.input_dir == Path('/tmp/test')

def test_path_operations_cross_platform():
    """Path operations work on all platforms."""
    base = Path('/tmp/test')
    result = base / 'subdir' / 'file.txt'

    # Path.__truediv__ works on all platforms
    assert 'subdir' in result.parts
    assert result.name == 'file.txt'

def test_as_posix_portability():
    """as_posix() produces portable paths."""
    # Windows
    win_path = Path('C:\\Users\\test')
    assert win_path.as_posix() == 'C:/Users/test'

    # Linux
    linux_path = Path('/home/user/test')
    assert linux_path.as_posix() == '/home/user/test'
```

### Integration Tests

```python
def test_subprocess_with_paths():
    """Subprocess calls work with Path objects."""
    from pathlib import Path
    import subprocess

    test_file = Path('/tmp/test.mp4')
    cmd = ['ffmpeg', '-i', str(test_file)]
    # Should work on all platforms
```

## Summary

### Key Principles

1. **Internal**: Always use `pathlib.Path` objects
2. **Config**: Properties return Path objects
3. **Subprocess**: Convert with `str(path)`
4. **Storage**: Use `path.as_posix()` for portability
5. **Display**: Use `str(path)` for familiarity

### Benefits

- ✅ **Cross-platform**: Works on Windows, Linux, macOS
- ✅ **Type-safe**: Path objects enable type checking
- ✅ **Clean code**: No manual slash handling
- ✅ **Portable**: TOML files use forward slashes
- ✅ **Correct**: Platform-aware path operations
- ✅ **Maintainable**: Clear, consistent pattern

### Anti-Patterns to Avoid

❌ `path = input_dir + "/" + filename` (manual joining)
❌ `path.replace("\\", "/")` (slash replacement)
❌ `os.path.join(input_dir, filename)` (use Path `/` instead)
❌ Mixing Path and str without conversion
❌ Storing Path objects in TOML/JSON (use strings)

---

**Remember: Path objects internally, strings only at boundaries!**
