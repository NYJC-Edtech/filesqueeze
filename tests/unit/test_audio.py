"""Test audio compression functionality (WAV -> AAC/M4A)."""

import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from filesqueeze.ops.audio import compress

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def write_sine_wav(path: Path, seconds: float = 2.0, frequency: int = 440, framerate: int = 44100) -> None:
    """Write a small mono 16-bit sine-wave WAV for testing."""
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        frames = bytearray()
        for i in range(int(framerate * seconds)):
            value = int(12000 * math.sin(2 * math.pi * frequency * i / framerate))
            frames += struct.pack("<h", value)
        w.writeframes(bytes(frames))


class TestAudioConfigAdapter:
    """Test the AudioConfig adapter used by the audio operation."""

    def test_defaults(self):
        from filesqueeze.config import Config
        from filesqueeze.system.config_adapters import AudioConfig

        adapter = AudioConfig(Config({}))

        assert adapter.audio_bitrate == "96k"
        assert adapter.threads == 8
        assert adapter.timeout == 1800
        assert adapter.min_output_size_bytes == 4096

    def test_custom_values(self):
        from filesqueeze.config import Config
        from filesqueeze.system.config_adapters import AudioConfig

        adapter = AudioConfig(
            Config(
                {
                    "ffmpeg": {"audio_bitrate": "64k", "threads": 2},
                    "processing": {"timeout_seconds": 60, "min_output_size_bytes": 100},
                }
            )
        )

        assert adapter.audio_bitrate == "64k"
        assert adapter.threads == 2
        assert adapter.timeout == 60
        assert adapter.min_output_size_bytes == 100


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg is not installed")
class TestAudioCompression:
    """Test audio compression with real FFmpeg."""

    def test_compress_wav_to_m4a_produces_smaller_file(self, tmp_path):
        """A WAV file compresses to a far smaller M4A."""
        infile = tmp_path / "input.wav"
        outfile = tmp_path / "output.m4a"
        write_sine_wav(infile, seconds=5.0)

        compress(str(infile), str(outfile))

        assert outfile.exists()
        assert outfile.stat().st_size > 0
        assert outfile.stat().st_size < infile.stat().st_size / 2

    def test_compress_with_config(self, tmp_path):
        """Compression works with a Config object providing settings."""
        from filesqueeze.config import Config

        infile = tmp_path / "input.wav"
        outfile = tmp_path / "output.m4a"
        write_sine_wav(infile, seconds=2.0)
        config = Config({"ffmpeg": {"audio_bitrate": "64k", "threads": 2}})

        compress(str(infile), str(outfile), config=config)

        assert outfile.exists()

    def test_compress_invalid_input_raises(self, tmp_path):
        """Non-audio bytes make FFmpeg fail with RuntimeError."""
        infile = tmp_path / "input.wav"
        infile.write_bytes(b"this is not audio content")
        outfile = tmp_path / "output.m4a"

        with pytest.raises(RuntimeError, match="FFmpeg failed to compress audio"):
            compress(str(infile), str(outfile))
        assert not outfile.exists()

    def test_compress_missing_input_raises(self, tmp_path):
        """A nonexistent input file surfaces as RuntimeError."""
        infile = tmp_path / "missing.wav"
        outfile = tmp_path / "output.m4a"

        with pytest.raises(RuntimeError):
            compress(str(infile), str(outfile))
