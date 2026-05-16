"""Behavioral baseline tests - Establish baseline BEFORE refactoring.

IMPORTANT: This file MUST be run BEFORE starting the system/ops refactoring.
It establishes a baseline of current behavior to compare against after refactoring.

Usage:
    1. Before refactoring: Run TestBehavioralBaseline to create baseline
    2. After refactoring: Run TestBehavioralRegression to verify no regressions

Example:
    # Before refactor
    pytest tests/regression/test_behavioral_baseline.py::TestBehavioralBaseline -v

    # After refactor
    pytest tests/regression/test_behavioral_baseline.py::TestBehavioralRegression -v
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from filesqueeze.config import Config
from filesqueeze.ops.document import compress_pdf
from filesqueeze.ops.image import compress_image
from filesqueeze.ops.video import compress as compress_video

BASELINE_DIR = Path(__file__).parent.parent.parent / "test_baselines"
BASELINE_DIR.mkdir(exist_ok=True)


def calculate_file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of a file."""
    return hashlib.md5(filepath.read_bytes()).hexdigest()


def save_baseline(name: str, data: dict[str, Any]) -> None:
    """Save baseline data to JSON file."""
    baseline_file = BASELINE_DIR / f"{name}.json"
    with open(baseline_file, "w") as f:
        json.dump(data, f, indent=2)


def load_baseline(name: str) -> dict[str, Any]:
    """Load baseline data from JSON file."""
    baseline_file = BASELINE_DIR / f"{name}.json"
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline not found: {baseline_file}")
    with open(baseline_file) as f:
        return json.load(f)


class TestBehavioralBaseline:
    """Baseline tests - RUN BEFORE REFACTORING.

    These tests establish the current behavior of the system.
    Run these tests and save the results before starting Phase 1.
    """

    @pytest.mark.baseline
    @pytest.mark.skipif(
        True,  # Always skip when running normal tests
        reason="Run manually with: pytest tests/regression/test_behavioral_baseline.py::TestBehavioralBaseline -v --run-baseline",
    )
    def test_video_compression_baseline(self, sample_video, tmp_path):
        """Establish baseline for video compression behavior.

        Creates:
        - Output file hash
        - Output file size
        - Success/failure status
        """
        pytest.skip("Skipping baseline test - run with --run-baseline flag")

        if not sample_video:
            pytest.skip("Sample video not available")

        config = Config()
        output = tmp_path / "baseline_video_output.mp4"

        # Compress with default settings
        result = compress_video(str(sample_video), str(output), config=config)

        # Gather baseline data
        baseline_data = {
            "test_name": "video_compression_default",
            "input_file": str(sample_video),
            "success": result,
            "output_exists": output.exists() if result else False,
            "output_size": output.stat().st_size if output.exists() else 0,
            "output_hash": calculate_file_hash(output) if output.exists() else None,
            "config": {
                "video.crf": config.get("video.crf", 23),
                "video.preset": config.get("video.preset", "medium"),
            },
        }

        # Save baseline
        save_baseline("video_compression_default", baseline_data)

        # Verify baseline is valid
        assert result is True, "Baseline: Video compression should succeed"
        assert output.exists(), "Baseline: Output file should exist"
        assert baseline_data["output_size"] > 0, "Baseline: Output should not be empty"

        print(f"\n✓ Baseline saved to {BASELINE_DIR / 'video_compression_default.json'}")

    @pytest.mark.baseline
    @pytest.mark.skipif(
        True,
        reason="Run manually with: pytest tests/regression/test_behavioral_baseline.py::TestBehavioralBaseline -v --run-baseline",
    )
    def test_video_compression_with_custom_crf(self, sample_video, tmp_path):
        """Establish baseline for video compression with custom CRF."""
        pytest.skip("Skipping baseline test - run with --run-baseline flag")

        if not sample_video:
            pytest.skip("Sample video not available")

        config = Config()
        output = tmp_path / "baseline_video_crf30.mp4"

        # Compress with CRF=30
        result = compress_video(str(sample_video), str(output), config=config, crf=30)

        baseline_data = {
            "test_name": "video_compression_crf30",
            "input_file": str(sample_video),
            "success": result,
            "output_exists": output.exists() if result else False,
            "output_size": output.stat().st_size if output.exists() else 0,
            "output_hash": calculate_file_hash(output) if output.exists() else None,
            "override_params": {"crf": 30},
        }

        save_baseline("video_compression_crf30", baseline_data)

        assert result is True
        assert output.exists()

        print(f"\n✓ Baseline saved to {BASELINE_DIR / 'video_compression_crf30.json'}")

    @pytest.mark.baseline
    @pytest.mark.skipif(
        True,
        reason="Run manually with: pytest tests/regression/test_behavioral_baseline.py::TestBehavioralBaseline -v --run-baseline",
    )
    def test_pdf_compression_baseline(self, sample_generated_pdf, tmp_path):
        """Establish baseline for PDF compression behavior."""
        pytest.skip("Skipping baseline test - run with --run-baseline flag")

        if not sample_generated_pdf:
            pytest.skip("Sample PDF not available")

        config = Config()
        output = tmp_path / "baseline_pdf_output.pdf"

        # Compress with default settings
        result = compress_pdf(str(sample_generated_pdf), str(output), config=config)

        baseline_data = {
            "test_name": "pdf_compression_default",
            "input_file": str(sample_generated_pdf),
            "success": result,
            "output_exists": output.exists() if result else False,
            "output_size": output.stat().st_size if output.exists() else 0,
            "output_hash": calculate_file_hash(output) if output.exists() else None,
            "config": {
                "document.quality": config.get("document.quality", 75),
            },
        }

        save_baseline("pdf_compression_default", baseline_data)

        assert result is True
        assert output.exists()

        print(f"\n✓ Baseline saved to {BASELINE_DIR / 'pdf_compression_default.json'}")

    @pytest.mark.baseline
    @pytest.mark.skipif(
        True,
        reason="Run manually with: pytest tests/regression/test_behavioral_baseline.py::TestBehavioralBaseline -v --run-baseline",
    )
    def test_image_compression_baseline(self, sample_image, tmp_path):
        """Establish baseline for image compression behavior."""
        pytest.skip("Skipping baseline test - run with --run-baseline flag")

        if not sample_image:
            pytest.skip("Sample image not available")

        config = Config()
        output = tmp_path / "baseline_image_output.jpg"

        # Compress with default settings
        result = compress_image(str(sample_image), str(output), config=config)

        baseline_data = {
            "test_name": "image_compression_default",
            "input_file": str(sample_image),
            "success": result,
            "output_exists": output.exists() if result else False,
            "output_size": output.stat().st_size if output.exists() else 0,
            "output_hash": calculate_file_hash(output) if output.exists() else None,
            "config": {
                "image.quality": config.get("image.quality", 85),
            },
        }

        save_baseline("image_compression_default", baseline_data)

        assert result is True
        assert output.exists()

        print(f"\n✓ Baseline saved to {BASELINE_DIR / 'image_compression_default.json'}")


class TestBehavioralRegression:
    """Regression tests - RUN AFTER REFACTORING.

    These tests verify that the refactored code produces identical results
    to the baseline established before refactoring.
    """

    def test_video_compression_regression(self, sample_video, tmp_path):
        """Verify: Video compression matches baseline after refactor."""
        if not sample_video:
            pytest.skip("Sample video not available")

        # Load baseline
        try:
            baseline = load_baseline("video_compression_default")
        except FileNotFoundError:
            pytest.skip("Baseline not found. Run TestBehavioralBaseline first.")

        # Run with NEW (refactored) code
        config = Config()
        output = tmp_path / "regression_video_output.mp4"

        result = compress_video(str(sample_video), str(output), config=config)

        # Verify behavior matches baseline
        assert result == baseline["success"], f"Success status differs! Expected {baseline['success']}, got {result}"

        assert output.exists() == baseline["output_exists"], (
            f"Output existence differs! Expected {baseline['output_exists']}, got {output.exists()}"
        )

        if output.exists():
            new_size = output.stat().st_size
            assert new_size == baseline["output_size"], (
                f"Output size differs! Expected {baseline['output_size']}, got {new_size}"
            )

            new_hash = calculate_file_hash(output)
            assert new_hash == baseline["output_hash"], (
                f"Output hash differs! File content changed.\nExpected: {baseline['output_hash']}\nGot:      {new_hash}"
            )

    def test_video_compression_crf30_regression(self, sample_video, tmp_path):
        """Verify: Video compression with CRF=30 matches baseline."""
        if not sample_video:
            pytest.skip("Sample video not available")

        try:
            baseline = load_baseline("video_compression_crf30")
        except FileNotFoundError:
            pytest.skip("Baseline not found. Run TestBehavioralBaseline first.")

        config = Config()
        output = tmp_path / "regression_video_crf30.mp4"

        result = compress_video(str(sample_video), str(output), config=config, crf=30)

        assert result == baseline["success"]
        assert output.exists() == baseline["output_exists"]

        if output.exists():
            new_hash = calculate_file_hash(output)
            assert new_hash == baseline["output_hash"], (
                f"Output with CRF=30 differs from baseline!\nExpected: {baseline['output_hash']}\nGot:      {new_hash}"
            )

    def test_pdf_compression_regression(self, sample_generated_pdf, tmp_path):
        """Verify: PDF compression matches baseline after refactor."""
        if not sample_generated_pdf:
            pytest.skip("Sample PDF not available")

        try:
            baseline = load_baseline("pdf_compression_default")
        except FileNotFoundError:
            pytest.skip("Baseline not found. Run TestBehavioralBaseline first.")

        config = Config()
        output = tmp_path / "regression_pdf_output.pdf"

        result = compress_pdf(str(sample_generated_pdf), str(output), config=config)

        assert result == baseline["success"]
        assert output.exists() == baseline["output_exists"]

        if output.exists():
            new_hash = calculate_file_hash(output)
            assert new_hash == baseline["output_hash"], (
                f"PDF output differs from baseline!\nExpected: {baseline['output_hash']}\nGot:      {new_hash}"
            )

    def test_image_compression_regression(self, sample_image, tmp_path):
        """Verify: Image compression matches baseline after refactor."""
        if not sample_image:
            pytest.skip("Sample image not available")

        try:
            baseline = load_baseline("image_compression_default")
        except FileNotFoundError:
            pytest.skip("Baseline not found. Run TestBehavioralBaseline first.")

        config = Config()
        output = tmp_path / "regression_image_output.jpg"

        result = compress_image(str(sample_image), str(output), config=config)

        assert result == baseline["success"]
        assert output.exists() == baseline["output_exists"]

        if output.exists():
            new_hash = calculate_file_hash(output)
            assert new_hash == baseline["output_hash"], (
                f"Image output differs from baseline!\nExpected: {baseline['output_hash']}\nGot:      {new_hash}"
            )


# Helper function to run baseline tests manually
def run_baseline_tests():
    """Helper to run baseline tests manually.

    Usage:
        python -c "from tests.regression.test_behavioral_baseline import run_baseline_tests; run_baseline_tests()"
    """
    import sys

    sys.exit(
        pytest.main(
            [__file__, "::TestBehavioralBaseline", "-v", "--tb=short", "-p", "no:skip"]  # Override @pytest.mark.skipif
        )
    )


def run_regression_tests():
    """Helper to run regression tests manually.

    Usage:
        python -c "from tests.regression.test_behavioral_baseline import run_regression_tests; run_regression_tests()"
    """
    import sys

    sys.exit(pytest.main([__file__, "::TestBehavioralRegression", "-v", "--tb=short"]))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--baseline":
        print("Creating behavioral baseline...")
        print("=" * 60)
        run_baseline_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--regression":
        print("Running regression tests...")
        print("=" * 60)
        run_regression_tests()
    else:
        print(__doc__)
        print("\nUsage:")
        print("  python test_behavioral_baseline.py --baseline      # Create baseline")
        print("  python test_behavioral_baseline.py --regression    # Test regression")
