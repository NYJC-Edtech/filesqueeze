"""Integration tests for standalone (single-file) compression.

Runs the real pipeline (Pillow for images - no external binaries needed)
to verify the dialog's compression path end to end, including the
compressed_<stem>.<ext> naming contract.
"""

from pathlib import Path

import pytest

from filesqueeze.standalone import compress_file, predict_output_path, resolve_final_output_path


@pytest.fixture
def runtime_config():
    """Config plus registered logger/binary finder, mirroring the dialog's runtime setup."""
    from filesqueeze.config import Config as ConfigClass
    from filesqueeze.logger import setup_logging
    from filesqueeze.system import register_binary_finder, register_logger
    from filesqueeze.system.binaries import BinaryFinder

    config = ConfigClass()
    register_logger(setup_logging(config))
    register_binary_finder(BinaryFinder(config))
    return config


class TestStandaloneCompression:
    def test_compress_image_to_chosen_destination(self, sample_image, tmp_path, runtime_config):
        input_path = Path(sample_image)
        destination = tmp_path / "out"
        destination.mkdir()

        predicted = predict_output_path(input_path, destination)
        assert predicted.name == f"compressed_{input_path.stem}.jpg"

        final_path, renamed = resolve_final_output_path(predicted)
        assert renamed is False

        result = compress_file(input_path, final_path, runtime_config)

        assert result.exists()
        assert result.stat().st_size > 0
        assert result.parent == destination

    def test_compress_image_name_collision_auto_renames(self, sample_image, tmp_path, runtime_config):
        input_path = Path(sample_image)
        destination = tmp_path / "out"
        destination.mkdir()

        predicted = predict_output_path(input_path, destination)
        first_result = compress_file(input_path, predicted, runtime_config)
        assert first_result.exists()

        # Second run against the same destination must not overwrite
        final_path, renamed = resolve_final_output_path(predicted)
        assert renamed is True

        second_result = compress_file(input_path, final_path, runtime_config)
        assert second_result.exists()
        assert second_result != first_result
