"""Unit tests for PowerPoint error handling."""

import tempfile
from pathlib import Path

import pytest

from filesqueeze import make_presentation
from filesqueeze.config import Config


def test_make_presentation_with_invalid_file():
    """Test that make_presentation raises RuntimeError when conversion fails."""
    # Create a fake PowerPoint file (just a text file with .pptx extension)
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(b'This is not a real PowerPoint file')
        tmp.flush()

    try:
        # Create a temporary output directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            config = Config()

            # This should raise RuntimeError because:
            # 1. The file is not a valid PowerPoint file
            # 2. PowerPoint will fail to open it
            # 3. The state machine will set ERROR status
            # 4. make_presentation should raise RuntimeError
            with pytest.raises(RuntimeError, match="File processing failed"):
                make_presentation(str(tmp_path), config=config, output_path=str(output_dir / "output.mp4"))
    finally:
        tmp_path.unlink()


def test_make_presentation_preserves_error_state():
    """Test that error state is preserved through cleanupFiles handler."""
    from filesqueeze.fsm import State, StateMachine
    from filesqueeze import handlers
    from filesqueeze.fsm.enums import Status

    # Create a state with an invalid PowerPoint file
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(b'Invalid PPTX content')
        tmp.flush()

    try:
        # Run state machine
        sm = StateMachine(start=handlers.selectAnalyzer)
        final_state = sm.run(str(tmp_path))

        # The final state should be ERROR, not COMPLETE
        assert final_state.status == Status.ERROR, f"Expected ERROR status, got {final_state.status}"

        # The target should be the original file (since conversion failed)
        assert final_state.target == tmp_path
    finally:
        tmp_path.unlink()


def test_cleanupFiles_preserves_error_status():
    """Test that cleanupFiles handler preserves ERROR status."""
    from filesqueeze.fsm import State
    from filesqueeze.fsm.enums import Status
    from filesqueeze import handlers

    # Create a temporary file for the state
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(b'Invalid PPTX')
        tmp.flush()

    try:
        # Create a state in ERROR status
        state = State(str(tmp_path))
        state.error("Test error")

        # Call cleanupFiles (which should preserve ERROR status)
        result = handlers.cleanupFiles(state)

        # Status should still be ERROR, not COMPLETE
        assert state.status == Status.ERROR, f"cleanupFiles should preserve ERROR status, got {state.status}"

        # cleanupFiles should return None to terminate state machine
        assert result is None
    finally:
        tmp_path.unlink()
