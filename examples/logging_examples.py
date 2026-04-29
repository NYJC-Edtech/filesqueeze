"""FileSqueeze Logging Examples

Practical examples showing the logging strategy in action.
Run this file to see structured logging output.
"""

import sys
from pathlib import Path

# Add filesqueeze to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from filesqueeze.fsm import Handler, State, StateMachine
from filesqueeze.tracelogger import setup_tracelogging, trace_context, trace_handler

# ============================================================================
# Example 1: Handler with Automatic Logging
# ============================================================================


@trace_handler
def analyzeFile(state: State) -> Handler:
    """Analyze a file - entry/exit automatically logged."""
    print(f"  Analyzing: {state.origin}")
    state.metadata["size"] = 1024
    state.metadata["format"] = "mp4"
    return compressFile


@trace_handler
def compressFile(state: State) -> Handler:
    """Compress a file - entry/exit automatically logged."""
    print(f"  Compressing: {state.origin}")

    # Simulate work
    import time

    time.sleep(0.1)

    # Simulate error scenario
    if state.metadata.get("format") == "corrupt":
        raise ValueError("File format is corrupt")

    return cleanupFiles


def cleanupFiles(state: State) -> Handler:
    """Cleanup - entry/exit automatically logged."""
    print(f"  Cleanup: {state.origin}")
    state.status_complete()
    return None  # End of state machine


def example_handler_logging():
    """Example: Automatic handler logging with @log_handler."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Handler Decorator - Automatic Entry/Exit Logging")
    print("=" * 70)

    # Setup logging
    logger = setup_tracelogging(log_file=None, level="INFO", console_format="human")  # Console only for this example

    # Run state machine (logging enabled by default via system logger)
    state_machine = StateMachine(start=analyzeFile)
    initial_state = State("/path/to/video.mp4")

    print("\nProcessing file...")
    final_state = state_machine.run(initial_state)
    print(f"Final status: {final_state.status}")


# ============================================================================
# Example 2: Handler with Exception Logging
# ============================================================================


@trace_handler
def compressFileWithError(state: State) -> Handler:
    """Handler that raises exception - automatically logged with traceback."""
    print(f"  Compressing (will fail): {state.origin}")

    # Simulate error
    raise ValueError("Simulated compression error")


def example_exception_logging():
    """Example: Automatic exception logging."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Exception Logging - Automatic Traceback Capture")
    print("=" * 70)

    logger = setup_tracelogging(level="INFO", console_format="human")

    state_machine = StateMachine(start=analyzeFile, enable_logging=True)
    initial_state = State("/path/to/corrupt.mp4")
    initial_state.metadata["format"] = "corrupt"

    print("\nProcessing file (will fail)...")
    try:
        final_state = state_machine.run(initial_state)
    except ValueError as e:
        print(f"Caught exception: {e}")
        print("  (Exception was automatically logged with traceback)")


# ============================================================================
# Example 3: Manual Logging with Context
# ============================================================================


def example_manual_logging():
    """Example: Manual logging with automatic context."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Manual Logging - Automatic Context (trace_id, file)")
    print("=" * 70)

    logger = setup_tracelogging(level="INFO", console_format="human")

    # Create state for context
    state = State("/path/to/document.pdf")

    # All logs within context automatically get trace_id, file, etc.
    with trace_context(state, workflow="manual"):
        logger.info("Starting manual processing workflow")

        # Custom fields are automatically included
        logger.info("Extracting metadata", page_count=10, author="John")

        logger.info("Processing complete", result="success")

    print("\n  ↑ All logs above automatically included:")
    print("    - trace_id (unique for this workflow)")
    print("    - file (document.pdf)")
    print("    - workflow (manual)")
    print("    - elapsed_ms (timing)")


# ============================================================================
# Example 4: JSON Structured Logging
# ============================================================================


def example_json_logging():
    """Example: JSON structured logging for production."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: JSON Structured Logging - Production Format")
    print("=" * 70)

    # Setup with JSON format
    logger = setup_tracelogging(log_file=None, level="INFO", console_format="json")  # JSON output

    print("\nJSON log output (machine-parseable):")

    # Run workflow
    state = State("/path/to/presentation.pptx")
    with trace_context(state, workflow="cli"):
        logger.info("Starting CLI workflow")
        logger.info("File detected", size=2048000, type="presentation")


# ============================================================================
# Example 5: Timeline Reconstruction
# ============================================================================


def example_timeline():
    """Example: Full execution timeline with timing."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Timeline Reconstruction - Full Execution Trace")
    print("=" * 70)

    logger = setup_tracelogging(level="INFO", console_format="human")

    print("\nFull execution trace with timing:")

    # Run complete workflow
    state_machine = StateMachine(start=analyzeFile, enable_logging=True)
    initial_state = State("/path/to/large_video.mp4")

    final_state = state_machine.run(initial_state)

    print("\n  ↑ Each log entry shows:")
    print("    - Handler name (operation)")
    print("    - Event type (entry/exit/transition)")
    print("    - Duration (how long each handler took)")
    print("    - Next handler (workflow progression)")


# ============================================================================
# Example 6: Before/After Comparison
# ============================================================================


def before_logging():
    """BEFORE: No logging, bare exception handler."""
    print("\n" + "-" * 70)
    print("BEFORE (Current State):")
    print("-" * 70)
    print(
        """
    def compressVideo(state):
        try:
            success = video.compress(str(state.target), str(output_path))
        except Exception:
            state.metadata['error'] = "Error during compression"
            return cleanupFiles
        return cleanupFiles
    """
    )
    print("\n  ❌ No logging - what went wrong?")
    print("  ❌ No traceback - where did it fail?")
    print("  ❌ No context - which file? which operation?")


def after_logging():
    """AFTER: Automatic logging with context."""
    print("\n" + "-" * 70)
    print("AFTER (With Structured Logging):")
    print("-" * 70)
    print(
        """
    @trace_handler  # ← Only change needed!
    def compressVideo(state):
        try:
            success = video.compress(str(state.target), str(output_path))
        except Exception as e:
            # Exception automatically logged with:
            # - Full traceback
            # - trace_id (file workflow identifier)
            # - file path
            # - operation name
            # - duration
            # - exception type and message
            state.metadata['error'] = str(e)
            raise
        return cleanupFiles
    """
    )
    print("\n  ✅ Automatic entry logging")
    print("  ✅ Automatic exit logging with timing")
    print("  ✅ Automatic exception logging with traceback")
    print("  ✅ Automatic context (trace_id, file, operation)")


def example_comparison():
    """Example: Before/after comparison."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Before/After Comparison")
    print("=" * 70)

    before_logging()
    after_logging()


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "FileSqueeze Logging Examples" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")

    # Run examples
    example_handler_logging()
    example_exception_logging()
    example_manual_logging()
    example_json_logging()
    example_timeline()
    example_comparison()

    print("\n" + "=" * 70)
    print("All examples complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. @log_handler decorator - automatic entry/exit logging")
    print("  2. Exceptions automatically logged with traceback")
    print("  3. log_context() - automatic trace_id and file context")
    print("  4. JSON format - production-ready, machine-parseable")
    print("  5. Timeline reconstruction - full execution trace")
    print("  6. Zero boilerplate - can't forget to log")
    print("\n")


if __name__ == "__main__":
    main()
