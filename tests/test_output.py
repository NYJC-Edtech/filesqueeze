"""Test output path generation and metadata handling."""

import json
import os
import time
from pathlib import Path
import pytest

from filesqueeze.output import (
    generate_output_path,
    save_metadata,
    preserve_timestamps,
    ensure_output_dir,
    get_unique_output_path
)
from filesqueeze.config import Config


class TestOutputPathGeneration:
    """Test output path generation."""

    def test_generate_output_path_flat(self, tmp_path):
        """Test flat structure."""
        input_path = Path('test.mp4')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, structure='flat')
        assert result == output_dir / 'test.mp4'

    def test_generate_output_path_by_type_video(self, tmp_path):
        """Test by_type structure for video."""
        input_path = Path('test.mp4')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, structure='by_type')
        assert result == output_dir / 'video' / 'test.mp4'

    def test_generate_output_path_by_type_document(self, tmp_path):
        """Test by_type structure for document."""
        input_path = Path('test.pdf')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, structure='by_type')
        assert result == output_dir / 'document' / 'test.pdf'

    def test_generate_output_path_by_type_image(self, tmp_path):
        """Test by_type structure for image."""
        input_path = Path('test.jpg')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, structure='by_type')
        assert result == output_dir / 'image' / 'test.jpg'

    def test_generate_output_path_by_date(self, tmp_path):
        """Test by_date structure."""
        input_path = tmp_path / 'test.mp4'
        input_path.write_text('test')
        output_dir = tmp_path / 'output'

        result = generate_output_path(input_path, output_dir, structure='by_date')
        # Should be in YYYY-MM-DD format
        assert result.parent.name.isdigit() or len(result.parent.name) == 10
        assert result.name == 'test.mp4'

    def test_generate_output_path_mirror_relative(self, tmp_path):
        """Test mirror structure with relative path."""
        input_path = Path('subdir/test.mp4')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, structure='mirror')
        assert result == output_dir / 'subdir' / 'test.mp4'

    def test_generate_output_path_invalid_structure(self, tmp_path):
        """Test invalid structure raises error."""
        input_path = Path('test.mp4')
        output_dir = tmp_path

        with pytest.raises(ValueError, match="Invalid structure"):
            generate_output_path(input_path, output_dir, structure='invalid')

    def test_generate_output_path_with_config(self, tmp_path):
        """Test output path generation with config."""
        config = Config({'output': {'structure': 'flat'}})
        input_path = Path('test.mp4')
        output_dir = tmp_path

        result = generate_output_path(input_path, output_dir, config=config)
        # Should use config structure (default is 'flat')
        assert result == output_dir / 'test.mp4'


class TestMetadataHandling:
    """Test metadata saving functionality."""

    def test_save_metadata_disabled_by_default(self, tmp_path):
        """Test metadata saving is disabled by default."""
        output_path = tmp_path / 'test.mp4'
        output_path.write_text('test')

        metadata_path = output_path.with_suffix('.json')

        save_metadata(output_path, {'test': 'data'})

        # Metadata file should not be created
        assert not metadata_path.exists()

    def test_save_metadata_enabled(self, tmp_path):
        """Test metadata saving when enabled."""
        output_path = tmp_path / 'test.mp4'
        output_path.write_text('test')

        config = Config({'output': {'save_metadata': True}})
        metadata = {'source': '/path/to/source.mp4', 'processed_at': '2024-01-01'}

        save_metadata(output_path, metadata, config=config)

        metadata_path = output_path.with_suffix('.json')
        assert metadata_path.exists()

        with open(metadata_path) as f:
            saved = json.load(f)
        assert saved == metadata

    def test_save_metadata_with_complex_data(self, tmp_path):
        """Test saving complex metadata."""
        output_path = tmp_path / 'test.pdf'
        output_path.write_text('test')

        config = Config({'output': {'save_metadata': True}})
        metadata = {
            'source': '/path/to/source.pdf',
            'processed_at': '2024-01-01T12:00:00',
            'size': 1024000,
            'original_size': 2048000,
            'compression_ratio': 0.5
        }

        save_metadata(output_path, metadata, config=config)

        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path) as f:
            saved = json.load(f)
        assert saved == metadata


class TestTimestampPreservation:
    """Test timestamp preservation functionality."""

    def test_preserve_timestamps_enabled_by_default(self, tmp_path):
        """Test timestamp preservation is enabled by default."""
        input_path = tmp_path / 'input.mp4'
        input_path.write_text('test')

        output_path = tmp_path / 'output.mp4'
        output_path.write_text('test')

        # Set specific timestamps
        atime = mtime = time.time() - 3600  # 1 hour ago
        os.utime(input_path, (atime, mtime))

        preserve_timestamps(input_path, output_path)

        # Check output has same timestamps
        output_stat = output_path.stat()
        # Allow small tolerance for filesystem precision
        assert abs(output_stat.st_atime - atime) < 1
        assert abs(output_stat.st_mtime - mtime) < 1

    def test_preserve_timestamps_disabled(self, tmp_path):
        """Test timestamp preservation when disabled."""
        input_path = tmp_path / 'input.mp4'
        input_path.write_text('test')

        output_path = tmp_path / 'output.mp4'
        output_path.write_text('test')

        # Set specific timestamps
        atime = mtime = time.time() - 3600  # 1 hour ago
        os.utime(input_path, (atime, mtime))

        config = Config({'output': {'preserve_timestamps': False}})
        preserve_timestamps(input_path, output_path, config=config)

        # Output should keep its current timestamps (recent)
        output_stat = output_path.stat()
        # Should be recent, not 1 hour ago
        assert abs(output_stat.st_mtime - time.time()) < 5


class TestOutputDirectory:
    """Test output directory handling."""

    def test_ensure_output_dir_exists(self, tmp_path):
        """Test ensuring output directory exists."""
        output_path = tmp_path / 'subdir1' / 'subdir2' / 'test.mp4'

        ensure_output_dir(output_path)

        assert output_path.parent.exists()
        assert output_path.parent.is_dir()

    def test_ensure_output_dir_already_exists(self, tmp_path):
        """Test ensuring output directory when it already exists."""
        output_dir = tmp_path / 'subdir'
        output_dir.mkdir()

        output_path = output_dir / 'test.mp4'

        # Should not raise error
        ensure_output_dir(output_path)
        assert output_path.parent.exists()


class TestUniqueOutputPath:
    """Test unique output path generation."""

    def test_get_unique_output_path_not_exists(self, tmp_path):
        """Test unique path when file doesn't exist."""
        output_path = tmp_path / 'test.mp4'

        result = get_unique_output_path(output_path)
        assert result == output_path

    def test_get_unique_output_path_exists(self, tmp_path):
        """Test unique path when file exists."""
        output_path = tmp_path / 'test.mp4'
        output_path.write_text('test')

        result = get_unique_output_path(output_path)
        assert result == tmp_path / 'test_1.mp4'
        assert not result.exists()

    def test_get_unique_output_path_multiple_exists(self, tmp_path):
        """Test unique path when multiple versions exist."""
        output_path = tmp_path / 'test.mp4'
        output_path.write_text('test')

        (tmp_path / 'test_1.mp4').write_text('test')
        (tmp_path / 'test_2.mp4').write_text('test')

        result = get_unique_output_path(output_path)
        assert result == tmp_path / 'test_3.mp4'

    def test_get_unique_output_path_max_attempts(self, tmp_path):
        """Test unique path when max attempts reached."""
        output_path = tmp_path / 'test.mp4'
        output_path.write_text('test')

        # Create many versions
        for i in range(1, 1002):
            (tmp_path / f'test_{i}.mp4').write_text('test')

        with pytest.raises(RuntimeError, match="Could not find unique output path"):
            get_unique_output_path(output_path, max_attempts=1000)
