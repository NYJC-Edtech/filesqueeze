# FileSqueeze Architecture Documentation

**Last Updated**: 2026-01-26
**Status**: ✅ System/Ops Refactoring Complete (100%)

## Overview

FileSqueeze is restructured into clean separation between **system-level services** and **business logic operations** with proper dependency injection and module registration patterns.

## Package Structure

```
filesqueeze/
├── system/                    # System-level services (infrastructure)
│   ├── __init__.py
│   ├── logger.py              # Module-level logger registration (lazy pattern)
│   ├── binaries.py            # Binary finder registration
│   ├── platform.py            # Platform services
│   ├── config_adapters.py     # Type-safe config adapters
│   └── decorators.py          # Function tracing decorators
│
├── utils/                     # Utility modules (shared functionality)
│   ├── __init__.py
│   └── subprocess_helper.py   # Centralized subprocess execution
│
├── ops/                       # Business logic operations
│   ├── __init__.py
│   ├── video.py               # Video compression operations
│   ├── document.py            # PDF compression + image re-exports
│   ├── image.py               # Image compression operations
│   └── presentation.py        # PowerPoint conversion (pptx)
│
├── fsm/                       # State machine
│   ├── __init__.py
│   ├── default.py             # State class and handlers
│   └── enums.py               # Format enumerations
│
├── handlers.py                # State machine handlers
├── service.py                 # Service mode (directory watching)
├── cli.py                     # CLI interface
├── config.py                  # Configuration management
├── logger.py                  # Logger setup (Logger.setup, setup_logging)
├── scanner.py                 # File scanner
├── ocr.py                     # OCR processing
├── gui.py                     # GUI window
├── tray.py                    # System tray service
├── autostart.py               # Auto-startup configuration
├── doctor.py                  # Diagnostic tool
└── output.py                  # Output file organization
```

## Dependency Rules

**Critical Rule**: `system` package must NEVER import from `ops` package.

```
ops → system ✅ (allowed)
system → ops ❌ (FORBIDDEN - causes circular dependency)
handlers → ops ✅ (allowed)
fsm → system ✅ (allowed - logger only)
service → handlers, fsm, system ✅ (allowed)
cli → ops, system ✅ (allowed)
```

## System Package (`system/`)

### Purpose
Infrastructure services that support business logic. These are registered at startup and injected as dependencies.

### Modules

#### `logger.py` - Logger Registration
- **Pattern**: Module-level logger with lazy registration
- **Key Functions**:
  - `register_logger(logger)` - Register logger at startup
  - `get_logger()` - Get registered logger (with fallback)
  - `logger` - Lazy proxy for module-level usage
- **Features**:
  - Thread-safe registration
  - Lazy proxy allows imports before registration
  - Automatic trace context enrichment
  - Structured logging support

#### `binaries.py` - Binary Finder
- **Purpose**: Detect FFmpeg, Ghostscript, Tesseract installations
- **Key Functions**:
  - `register_binary_finder(finder)` - Register at startup
  - `get_binary_finder()` - Get registered finder
  - `BinaryFinder` class - Auto-detection logic
- **Features**:
  - Config-driven binary paths
  - Cached path lookups
  - Platform-specific detection (Windows/Linux)

#### `platform.py` - Platform Services
- **Purpose**: Platform detection and utilities
- **Key Functions**:
  - `is_windows()`, `is_linux()`, `is_mac()` - Platform detection
  - `get_platform()` - Get platform name
  - `get_architecture()`, `is_64bit()` - Architecture detection

#### `config_adapters.py` - Type-Safe Config
- **Purpose**: Validated configuration access
- **Classes**:
  - `VideoConfig` - FFmpeg settings (CRF, preset, threads, max_height)
  - `DocumentConfig` - PDF settings (quality, compression, JPEG conversion)
  - `ImageConfig` - Image settings (quality, max dimensions)
  - `PresentationConfig` - PPTX settings (CRF, preset)
- **Features**:
  - Validation on construction
  - Type-safe property access
  - Clear error messages for invalid values

#### `decorators.py` - Function Tracing
- **Purpose**: Automatic logging for function calls
- **Decorators**:
  - `@trace_function` - Entry/exit/timing/exception logging
  - `@trace_function_async` - Async version (for future use)

#### Trace Logging Features
- `TraceContext` - Holds trace context (trace_id, file_path, workflow)
- `trace_context()` - Context manager for automatic context enrichment
- `trace_handler` - Decorator for FSM handler tracing
- `log_transition()` - Log state machine transitions
- `StructuredFormatter` - JSON formatter for production logs

## Utils Package (`utils/`)

### Purpose
Shared utility modules providing common functionality across the application. These modules contain reusable components that are used by multiple other packages.

### Modules

#### `subprocess_helper.py` - Subprocess Utilities
- **Functions**:
  - `run_subprocess(cmd, timeout, tool_name, input_file, ...)` - Centralized subprocess execution
  - `verify_output_file(output_path, min_size, ...)` - Standardized file verification
  - `get_windows_subprocess_config()` - Windows subprocess configuration

- **Classes**:
  - `SubprocessError` - Enhanced error class with return_code, stdout, stderr
  - `SubprocessTimeout` - Timeout-specific error class

- **Features**:
  - Platform-specific subprocess configuration (Windows console hiding)
  - Consistent error handling across all operations
  - Enhanced error messages with context (return codes, stderr, tool names)
  - Standardized timeout and failure behavior
  - Thread-safe subprocess execution

- **Design Benefits**:
  - **Eliminates code duplication** - Single implementation of subprocess logic
  - **Improves consistency** - All operations use same approach
  - **Enhances testability** - Mockable utility functions
  - **Better error context** - More debugging information in errors

### Usage Pattern
```python
# Instead of duplicated subprocess.run() calls:
from filesqueeze.utils.subprocess_helper import run_subprocess, verify_output_file

# In ops modules:
run_subprocess(cmd, timeout=60, tool_name="FFmpeg", input_file=infile)
verify_output_file(outfile, min_size=100)
```

### Dependency Rules
- **system** → **utils** ✅ (allowed)
- **ops** → **utils** ✅ (allowed)
- **utils** → **system** ✅ (allowed)
- **utils** → **ops** ❌ (FORBIDDEN - would create circular dependency)

## Ops Package (`ops/`)

### Purpose
Business logic for file compression operations. These modules import from `system` package.

### Modules

#### `video.py` - Video Compression
- **Functions**:
  - `compress(input, output, config, crf, threads, preset, max_height, audio_bitrate)` - Compress video
  - `width_height(filepath)` - Get video dimensions
  - `duration(filepath)` - Get video duration
  - `get_ffmpeg_path()` - Get FFmpeg executable
  - `get_ffprobe_path()` - Get ffprobe executable
- **Uses**: `VideoConfig`, `BinaryFinder`, `@trace_function`

#### `document.py` - PDF Compression
- **Functions**:
  - `compress_pdf(input, output, config, quality)` - Compress PDF
  - `get_ghostscript_path()` - Get Ghostscript executable
- **Re-exports**: `compress_image`, `get_image_size` from `ops.image`
- **Uses**: `DocumentConfig`, `BinaryFinder`, `@trace_function`

#### `image.py` - Image Compression
- **Functions**:
  - `compress_image(input, output, config, quality)` - Compress image
  - `get_image_size(filepath)` - Get image dimensions
  - `get_ffmpeg_path()` - Get FFmpeg executable (for image ops)
- **Uses**: `ImageConfig`, `BinaryFinder`, `@trace_function`

#### `presentation.py` - PowerPoint Conversion
- **Functions**:
  - `to_mp4(input, output, config)` - Convert PPTX to MP4
  - `convert_pptx` - Alias for `to_mp4`
- **Uses**: `PresentationConfig`, `BinaryFinder`, `@trace_function`

## Startup Registration Pattern

### Entry Points Register Dependencies

**CLI Commands** (`cli.py`):
```python
from filesqueeze.logger import setup_logging
from filesqueeze.system import register_logger, register_binary_finder

logger = setup_logging(config)
register_logger(logger)
register_binary_finder(BinaryFinder(config))
```

**Service Mode** (`service.py`):
```python
from filesqueeze.system import register_logger, register_binary_finder
from filesqueeze.system.binaries import BinaryFinder

logger = setup_logging(...)
register_logger(logger)
register_binary_finder(BinaryFinder(config))
```

**Tray Service** (`tray.py`):
```python
from filesqueeze.system import register_logger

logger = setup_logging(...)
register_logger(logger)
```

### Ops Modules Use Registered Dependencies

```python
# In ops/video.py
from filesqueeze.system import logger
from filesqueeze.system.binaries import get_binary_finder
from filesqueeze.system.config_adapters import VideoConfig

def compress(input_path, output_path, config=None):
    # Use registered logger
    logger.info("Compressing video")

    # Use registered binary finder
    finder = get_binary_finder()
    ffmpeg_path = finder.get_ffmpeg_path()

    # Use validated config
    if config:
        video_config = VideoConfig(config)
```

## Configuration Cascade

**Priority** (highest to lowest):
1. Environment variables (`FILESQUEEZE_*`)
2. User config (`~/.config/filesqueeze/config.toml`)
3. Project config (`./filesqueeze.toml`)
4. Default config (`filesqueeze/default.toml`)

**Path Expansion**:
- All paths with `~` or environment variables are expanded once during config initialization
- `config.get()` always returns expanded, ready-to-use paths
- No need for `expanduser()` calls throughout codebase

## Testing Strategy

### Test Safety Rules

**CRITICAL**: Tests must NEVER modify production state:
- Use `tmp_path` fixture for temporary files
- Use mock configs instead of real user config
- `conftest.py` has protection to prevent writes to `~/.config/filesqueeze/config.toml`

### Test Structure

```
tests/
├── system/                    # System package tests
│   ├── test_config_adapters.py
│   └── test_logger.py
├── integration/               # Integration tests
│   ├── test_gui_behavior.py
│   ├── test_installers.py
│   ├── test_invariants.py
│   └── test_single_instance.py
├── regression/                # Regression tests
│   └── test_behavioral_baseline.py
├── test_*.py                  # Unit/integration tests
└── conftest.py                # Test configuration with safety guards
```

## Key Design Patterns

### 1. Dependency Injection
- Services (logger, binary finder) registered at startup
- Ops modules receive dependencies via `get_*()` functions
- Enables testing with mocks

### 2. Lazy Registration
- Ops modules import at module load time
- Dependencies not available until startup
- Lazy proxy (`logger`) defers lookup until use

### 3. Config Adapters
- Type-safe wrapper around raw config dict
- Validates on construction
- Clear error messages for invalid values

### 4. Function Tracing
- `@trace_function` decorator adds automatic logging
- Logs entry, exit, duration, exceptions
- Uses registered logger

## Migration from Old Structure

### Removed Files (Backward Compatibility Removed)
- `filesqueeze/video.py` (wrapper) → Use `filesqueeze.ops.video`
- `filesqueeze/document.py` (wrapper) → Use `filesqueeze.ops.document`
- `filesqueeze/pptx.py` (wrapper) → Use `filesqueeze.ops.presentation`
- `filesqueeze/binaries.py` (wrapper) → Use `filesqueeze.system.binaries`
- `filesqueeze/tracelogger.py` → Merged into `filesqueeze.system.logger`

### Updated Imports

**Old (No Longer Works)**:
```python
from filesqueeze.video import compress
from filesqueeze.document import compress_pdf
from filesqueeze.binaries import BinaryFinder
```

**New (Correct)**:
```python
from filesqueeze.ops.video import compress
from filesqueeze.ops.document import compress_pdf
from filesqueeze.system.binaries import BinaryFinder
```

### Kept Files
- `filesqueeze/logger.py` - Contains `Logger.setup()` and `setup_logging()`
  - These are actual functions, not wrappers
  - Used to configure logging at startup
  - Register logger with system via `register_logger()`

## Performance Considerations

- Config loaded once at startup
- Binary paths cached in `BinaryFinder`
- Logger lookups are lazy (cached in proxy)
- Trace context uses thread-local storage (thread-safe)

## Security Notes

- Tests are prevented from modifying user config (via `conftest.py`)
- No hardcoded paths (all configurable)
- Input validation via config adapters
- Safe path expansion (no injection)

## Future Enhancements

Potential areas for future improvement:
1. Add retry logic for transient failures
2. Create FileTypeRegistry abstraction
3. Standardize error handling with custom exceptions
4. Add platform abstraction for notifications
5. Implement proper cleanup for TODO comments in handlers

## Documentation

See also:
- `TESTING.md` - Testing guidelines and safety rules
- `PATH_HANDLING.md` - Cross-platform path handling design
- `README.md` - User documentation
