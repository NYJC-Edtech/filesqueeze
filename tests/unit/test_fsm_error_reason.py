"""Unit tests for error-reason propagation through the FSM.

``State.error(msg)`` records the reason so ``make_*`` can surface the
actionable cause (e.g. ``binary_not_found: ffmpeg ...``) instead of a
bare "File processing failed". Imports of ``filesqueeze`` modules happen
INSIDE the test functions (circular-import test discipline).
"""

import pytest


def test_state_records_error_message(tmp_path):
    from filesqueeze.fsm.default import State

    # State stats the origin at construction, so it must exist
    infile = tmp_path / "video.mp4"
    infile.write_bytes(b"dummy")

    state = State(infile)
    assert state.error_message is None

    state.error("binary_not_found: ffmpeg (test)")
    assert state.error_message == "binary_not_found: ffmpeg (test)"
    assert state.as_dict()["error_message"] == "binary_not_found: ffmpeg (test)"


def test_make_video_surfaces_binary_not_found_reason(tmp_path, monkeypatch):
    """A missing binary during compression reaches the RuntimeError text."""
    from filesqueeze.config import Config
    from filesqueeze.system.binaries import BinaryNotFoundError

    infile = tmp_path / "clip.mp4"
    infile.write_bytes(b"dummy")

    missing = BinaryNotFoundError("binary_not_found: ffmpeg (unit-test)")

    import filesqueeze.ops.video as video_ops

    monkeypatch.setattr(video_ops, "duration", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(video_ops, "width_height", lambda *_a, **_k: (0, 0), raising=True)

    def _fail_compress(*_a, **_k):
        raise missing

    import filesqueeze.handlers as handlers_module

    monkeypatch.setattr(handlers_module.video, "compress", _fail_compress)

    from filesqueeze import make_video

    with pytest.raises(RuntimeError) as excinfo:
        make_video(str(infile), config=Config({}))
    message = str(excinfo.value)
    assert "File processing failed" in message
    assert "binary_not_found: ffmpeg (unit-test)" in message
