# FileSqueeze Logging Strategy

## Executive Summary

FileSqueeze uses **automatic, structured logging** that requires zero manual logger calls in handler code. Logging happens through:
1. **State machine instrumentation** - Every transition automatically logged
2. **Handler decorators** - Entry/exit logged via `@log_handler`
3. **Trace context** - Unique ID follows each file through entire workflow
4. **Structured output** - JSON format for production analysis

**Key Benefit**: You can't forget to log. The framework does it for you.

---

## Design Philosophy

### Principles

1. **Automatic over Manual**
   - Logging happens via framework, not manual logger calls
   - Reduces human error and forgetting to log
   - Consistent logging across all code

2. **Context-Rich**
   - Every log entry carries: trace ID, file path, operation, timing
   - Enables full reconstruction of execution flow
   - Makes debugging production issues feasible

3. **Structured**
   - Machine-parseable JSON format
   - Enables aggregation (ELK, Splunk, CloudWatch)
   - Supports queries like "all errors for trace_id=abc123"

4. **Non-Brittle**
   - Can't forget to log entry/exit points
   - Can't forget to log exceptions
   - New features automatically get logging

5. **Retraceable**
   - Full trace from file discovery → completion/error
   - Timing data at each step for performance analysis
   - Exception stacktraces with full context

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: State Machine Instrumentation                      │
│  - Every state transition automatically logged               │
│  - Trace ID generated at file discovery                      │
│  - Timing data captured at each transition                   │
│  Location: fsm/__init__.py (StateMachine.transition())       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Handler Decorator                                  │
│  - @log_handler decorator on all handler functions           │
│  - Automatic entry/exit logging with timing                  │
│  - Exception capture with full context + traceback           │
│  Location: logging_structured.py (log_handler)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Structured Context Logger                          │
│  - Fluent API for building log context                       │
│  - Binds trace ID, file path, operation metadata             │
│  - Outputs JSON for log aggregation                          │
│  Location: logging_structured.py (FileSqueezeLogger)         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: Configurable Output                                │
│  - Console: Human-readable during dev                        │
│  - File: JSON for production analysis                        │
│  - Rotate by size/time to prevent disk bloat                │
│  Location: logging_structured.py (setup_structured_logging)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### 1. Basic Handler (Recommended)

```python
from filesqueeze.logging_structured import log_handler

@log_handler  # ← Only decorator needed, no logger calls
def compressVideo(state: State) -> Handler:
    state.status_compress()
    output_path = state.get_output_path()

    success = video.compress(
        str(state.target),
        str(output_path),
        state.config
    )

    if not success:
        state.metadata['error'] = "Video compression failed"
        return cleanupFiles  # Error automatically logged

    state.set_target(output_path)
    return cleanupFiles
```

**Automatically produces:**
```json
{"timestamp": "2026-01-26T10:15:23.456Z", "level": "INFO", "trace_id": "abc123", "file": "video.mp4", "operation": "compressVideo", "event": "entry"}
{"timestamp": "2026-01-26T10:15:45.789Z", "level": "INFO", "trace_id": "abc123", "file": "video.mp4", "operation": "compressVideo", "event": "exit", "duration_ms": 22333, "next_handler": "cleanupFiles"}
```

### 2. Manual Logging with Context

```python
from filesqueeze.logging_structured import log_context, get_logger

logger = get_logger()

def process_pdf(filepath: Path):
    # Automatically adds trace_id, file to all log entries
    with log_context(state, workflow="watch"):
        logger.info("Starting PDF processing")

        # Your custom logs get context automatically
        logger.info("Extracting pages", page_count=10)

        try:
            result = pdf_process(filepath)
            logger.info("Processing complete", result="success")
        except Exception as e:
            logger.error("Processing failed", exc_info=True)
```

**Produces:**
```json
{"timestamp": "...", "level": "INFO", "message": "Starting PDF processing", "context": {"trace_id": "def456", "file": "document.pdf", "workflow": "watch", "elapsed_ms": 5}}
{"timestamp": "...", "level": "INFO", "message": "Extracting pages", "context": {"trace_id": "def456", "file": "document.pdf", "page_count": 10, "elapsed_ms": 150}}
{"timestamp": "...", "level": "ERROR", "message": "Processing failed", "context": {...}, "exception": {"type": "ValueError", "message": "Invalid PDF"}}
```

### 3. Service Mode with Trace Context

```python
from filesqueeze.logging_structured import setup_structured_logging, log_context

# In service.py
class FileWatchService:
    def __init__(self, config: Config):
        self.config = config
        setup_structured_logging(config, log_file=config.log_file)

    def process_file(self, filepath: Path):
        # Create trace context for entire workflow
        with log_context(
            state=state,
            workflow="watch",
            file_size=filepath.stat().st_size
        ):
            # State machine automatically logs transitions
            final_state = self.state_machine.run(
                filepath,
                output_path=self.output_dir / filepath.name,
                config=self.config
            )

            # Workflow complete, auto-logs elapsed time
```

---

## Log Entry Structure

### JSON Format (File Logs)

```json
{
  "timestamp": "2026-01-26T10:15:23.456789Z",
  "level": "INFO",
  "logger": "filesqueeze",
  "message": "Handler entry: compressVideo",
  "context": {
    "trace_id": "abc12345",
    "file": "/path/to/video.mp4",
    "workflow": "watch",
    "handler": "compressVideo",
    "elapsed_ms": 1234,
    "file_size": 104857600
  },
  "operation": "compressVideo",
  "event": "entry",
  "duration_ms": null
}
```

### Human Format (Console Logs)

```
2026-01-26 10:15:23 - filesqueeze - INFO - Handler entry: compressVideo
2026-01-26 10:15:45 - filesqueeze - INFO - Handler exit: compressVideo (duration_ms=22333, next_handler=cleanupFiles)
```

---

## Event Types

### 1. Handler Entry
```json
{"event": "entry", "operation": "compressVideo"}
```
Logged when handler is called.

### 2. Handler Exit
```json
{"event": "exit", "operation": "compressVideo", "duration_ms": 1234, "next_handler": "cleanupFiles"}
```
Logged when handler returns successfully.

### 3. Handler Exception
```json
{
  "event": "exception",
  "operation": "compressVideo",
  "exception_type": "ValueError",
  "exception_message": "Invalid CRF value",
  "duration_ms": 456
}
```
Logged when handler raises exception.

### 4. State Transition
```json
{
  "event": "transition",
  "from_handler": "analyzeVideo",
  "to_handler": "compressVideo",
  "status": "COMPRESS"
}
```
Logged by StateMachine between handlers.

---

## Log Levels

### When to Use Each Level

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostics (disabled in prod) | "Page 5/100: OCR processing", "ffmpeg command: /usr/bin/ffmpeg -i ..." |
| **INFO** | Normal operation (default) | "Handler entry: compressVideo", "State transition: analyze → compress", "Processing complete" |
| **WARNING** | Unexpected but recoverable | "OCR failed for page 5, using fallback", "Video compression took 45s (expected <30s)" |
| **ERROR** | Operation failed, error handling worked | "Video compression failed: invalid CRF", "PDF processing failed: ghostscript not found" |
| **CRITICAL** * System-level failure | "Cannot start service: input directory missing", "Log file not writable" |

### Error Handling Policy

**Recoverable Errors:**
- Log at ERROR level with `exc_info=True`
- Add error to `state.metadata['error']`
- Return cleanup handler to continue workflow
- Example: OCR fails for one page, continue with rest

**Critical Errors:**
- Log at CRITICAL level with `exc_info=True`
- Raise exception to terminate workflow
- Example: Input directory doesn't exist, config invalid

**Never:**
- Silently ignore exceptions (use bare `except:`)
- Log without context (always include trace_id, file)
- Return False without logging (unactionable)

---

## Configuration

### Setup in Service Mode

```python
from filesqueeze.logging_structured import setup_structured_logging

# Automatic setup from config
logger = setup_structured_logging(
    config=config,
    log_file="~/FileSqueeze/filesqueeze.log",
    level="INFO",
    console_format="human"  # or "json"
)
```

### Config File (default.toml)

```toml
[logging]
file = "~/FileSqueeze/filesqueeze.log"
level = "INFO"
format = "detailed"
max_bytes = 10485760  # 10MB
backup_count = 5
rotation_type = "size"  # or "time"
```

---

## Tracing Workflows

### Finding All Logs for a File

```bash
# JSON logs (file)
jq 'select(.context.trace_id == "abc12345")' filesqueeze.log

# Human logs (grep)
grep "abc12345" filesqueeze.log
```

### Timeline Reconstruction

```json
[
  {"event": "entry", "operation": "analyzeVideo", "elapsed_ms": 0},
  {"event": "exit", "operation": "analyzeVideo", "elapsed_ms": 234, "next_handler": "compressVideo"},
  {"event": "transition", "from": "analyzeVideo", "to": "compressVideo"},
  {"event": "entry", "operation": "compressVideo", "elapsed_ms": 235},
  {"event": "exit", "operation": "compressVideo", "elapsed_ms": 15432, "next_handler": "cleanupFiles"}
]
```

Full execution trace with timing for every operation.

### Performance Analysis

```bash
# Average compression time for videos
jq 'select(.operation == "compressVideo" and .event == "exit") | .duration_ms' filesqueeze.log | awk '{sum+=$1; count++} END {print sum/count}'
```

---

## Migration Guide

### Before (Bare Exception Handler)

```python
def compressVideo(state: State) -> Handler:
    try:
        success = video.compress(str(state.target), str(output_path), state.config)
    except Exception:
        state.metadata['error'] = "Error during compression"
        return cleanupFiles
```

**Problem**: No logging, no traceback, impossible to debug.

### After (Structured Logging)

```python
@log_handler
def compressVideo(state: State) -> Handler:
    try:
        success = video.compress(str(state.target), str(output_path), state.config)
    except Exception as e:
        # Exception automatically logged with full traceback
        state.metadata['error'] = str(e)
        raise  # Or return cleanupFiles
```

**Result**: Automatic entry/exit logging, exception captured with traceback and context.

---

## Testing

### Unit Test Example

```python
def test_handler_logging(caplog):
    """Test that handler decorator logs entry/exit."""
    from filesqueeze.logging_structured import log_handler, get_logger

    @log_handler
    def test_handler(state):
        return "next_handler"

    state = State("/path/to/file.mp4")
    with caplog.at_level(logging.INFO):
        result = test_handler(state)

    # Verify logs
    assert "Handler entry: test_handler" in caplog.records[0].message
    assert "Handler exit: test_handler" in caplog.records[1].message
    assert caplog.records[1].duration_ms > 0
```

---

## Best Practices

### DO ✅

1. **Use `@log_handler` decorator** on all handler functions
2. **Use `log_context()`** for workflows outside handlers
3. **Log at appropriate levels** (INFO for normal, ERROR for failures)
4. **Include `exc_info=True`** when logging exceptions
5. **Add custom fields** to logs: `logger.info("Processing", page_count=10)`
6. **Let exceptions propagate** if you want them logged automatically

### DON'T ❌

1. **Don't use bare `except:`** - loses traceback, makes debugging impossible
2. **Don't forget to log** - the decorator does it for you
3. **Don't log without context** - use `log_context()` to add trace_id
4. **Don't log sensitive data** - file paths are OK, passwords are not
5. **Don't log in loops** - log summary instead: `logger.info("Processed 100 pages")`

---

## Troubleshooting

### Logs Not Appearing

1. Check log level: Is it set to INFO or lower?
2. Check log file: Does the directory exist? Is it writable?
3. Check handler: Is `@log_handler` applied to the function?

### Missing Trace ID

1. Ensure `log_context()` is used before calling handlers
2. Check State object has `origin` attribute
3. Verify `enable_logging=True` in StateMachine constructor

### Performance Issues

1. Too many DEBUG logs in production? Set level to INFO
2. Log file too large? Enable rotation in config
3. Logging overhead? Use async logging (future enhancement)

---

## Future Enhancements

1. **Async Logging** - Non-blocking log writes for high throughput
2. **Log Aggregation** - Built-in support for ELK, Splunk, CloudWatch
3. **Metrics** - Automatic extraction of timing metrics
4. **Alerting** - Integration with monitoring systems (PagerDuty, etc.)
5. **Distributed Tracing** - OpenTelemetry support for cross-service tracing

---

## References

- **Implementation**: [filesqueeze/logging_structured.py](../filesqueeze/logging_structured.py)
- **State Machine**: [filesqueeze/fsm/__init__.py](../filesqueeze/fsm/__init__.py)
- **Config**: [filesqueeze/default.toml](../filesqueeze/default.toml)
- **Examples**: [examples/logging_examples.py](../examples/logging_examples.py)

---

**Last Updated**: 2026-01-26
**Status**: ✅ Implemented and tested
