"""Unit tests for standalone (single-file) compression logic."""

from pathlib import Path
from unittest.mock import patch

import pytest

from filesqueeze.config import Config
from filesqueeze.standalone import (
    STANDALONE_UNSUPPORTED_MESSAGE,
    UnsupportedFileTypeError,
    build_filetypes,
    compress_file,
    describe_result,
    detect_category,
    format_size,
    output_extension_for,
    predict_output_path,
    resolve_final_output_path,
)


class TestDetectCategory:
    def test_video_extension_returns_video(self):
        assert detect_category("mp4") == "video"

    def test_pdf_extension_returns_pdf(self):
        assert detect_category("pdf") == "pdf"

    def test_image_extension_returns_image(self):
        assert detect_category("png") == "image"

    def test_presentation_extension_returns_presentation(self):
        assert detect_category("pptx") == "presentation"

    def test_unknown_extension_returns_none(self):
        assert detect_category("docx") is None

    def test_dot_prefix_and_case_are_normalized(self):
        assert detect_category(".MP4") == "video"


class TestOutputExtensionFor:
    def test_video_keeps_extension(self, tmp_path):
        assert output_extension_for(tmp_path / "clip.mp4") == ".mp4"

    def test_pdf_keeps_extension(self, tmp_path):
        assert output_extension_for(tmp_path / "doc.pdf") == ".pdf"

    def test_png_converts_to_jpg(self, tmp_path):
        assert output_extension_for(tmp_path / "photo.png") == ".jpg"

    def test_jpg_keeps_extension(self, tmp_path):
        assert output_extension_for(tmp_path / "photo.jpg") == ".jpg"

    def test_webp_converts_to_jpg(self, tmp_path):
        assert output_extension_for(tmp_path / "photo.webp") == ".jpg"


class TestPredictOutputPath:
    """Pin the compressed_<stem>.<ext> naming contract shared with monitoring mode."""

    def test_video_gets_compressed_prefix_in_destination(self, tmp_path):
        input_path = tmp_path / "clip.mp4"
        destination = tmp_path / "out"

        predicted = predict_output_path(input_path, destination)

        assert predicted == destination / "compressed_clip.mp4"

    def test_png_predicts_jpg_output(self, tmp_path):
        input_path = tmp_path / "photo.png"
        destination = tmp_path / "out"

        predicted = predict_output_path(input_path, destination)

        assert predicted == destination / "compressed_photo.jpg"

    def test_jpg_predicts_compressed_prefixed_name(self, tmp_path):
        input_path = tmp_path / "photo.jpg"
        destination = tmp_path / "out"

        predicted = predict_output_path(input_path, destination)

        assert predicted == destination / "compressed_photo.jpg"


class TestResolveFinalOutputPath:
    def test_no_conflict_returns_predicted_path(self, tmp_path):
        predicted = tmp_path / "compressed_clip.mp4"

        final, renamed = resolve_final_output_path(predicted)

        assert final == predicted
        assert renamed is False

    def test_conflict_auto_renames_with_counter(self, tmp_path):
        predicted = tmp_path / "compressed_clip.mp4"
        predicted.write_bytes(b"existing")

        final, renamed = resolve_final_output_path(predicted)

        assert renamed is True
        assert final == tmp_path / "compressed_clip_1.mp4"


class TestCompressFileDispatch:
    def make_config(self):
        return Config({"directories": {"input": "/tmp", "output": "/tmp"}})

    def test_video_dispatches_to_make_video(self, tmp_path):
        input_path = tmp_path / "clip.mp4"
        output_path = tmp_path / "compressed_clip.mp4"
        config = self.make_config()

        with patch("filesqueeze.make_video", return_value=str(output_path)) as mock_make:
            result = compress_file(input_path, output_path, config)

        mock_make.assert_called_once_with(str(input_path), config=config, output_path=str(output_path))
        assert result == Path(output_path)

    def test_pdf_dispatches_to_make_pdf(self, tmp_path):
        input_path = tmp_path / "doc.pdf"
        output_path = tmp_path / "compressed_doc.pdf"

        with patch("filesqueeze.make_pdf", return_value=str(output_path)) as mock_make:
            result = compress_file(input_path, output_path, self.make_config())

        mock_make.assert_called_once()
        assert result == Path(output_path)

    def test_image_dispatches_to_make_image(self, tmp_path):
        input_path = tmp_path / "photo.png"
        output_path = tmp_path / "compressed_photo.jpg"

        with patch("filesqueeze.make_image", return_value=str(output_path)) as mock_make:
            result = compress_file(input_path, output_path, self.make_config())

        mock_make.assert_called_once()
        assert result == Path(output_path)

    def test_presentation_raises_unsupported(self, tmp_path):
        input_path = tmp_path / "slides.pptx"
        output_path = tmp_path / "compressed_slides.mp4"

        with pytest.raises(UnsupportedFileTypeError, match="PowerPoint"):
            compress_file(input_path, output_path, self.make_config())

    def test_unknown_type_raises_unsupported(self, tmp_path):
        input_path = tmp_path / "file.docx"
        output_path = tmp_path / "compressed_file.docx"

        with pytest.raises(UnsupportedFileTypeError):
            compress_file(input_path, output_path, self.make_config())

    def test_unsupported_message_is_stable(self):
        assert "PowerPoint" in STANDALONE_UNSUPPORTED_MESSAGE
        assert "standalone" in STANDALONE_UNSUPPORTED_MESSAGE


class TestFormatSize:
    def test_bytes(self):
        assert format_size(512) == "512 B"

    def test_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert format_size(int(3.5 * 1024**3)) == "3.5 GB"


class TestDescribeResult:
    def test_smaller_output_reports_percentage(self):
        description = describe_result(400, 100)

        assert description == "400 B → 100 B (75% smaller)"

    def test_larger_output_reported_honestly(self):
        description = describe_result(100, 400)

        assert "400 B" in description
        assert "not smaller" in description


class TestBuildFiletypes:
    def test_includes_all_supported_group_with_common_types(self):
        filetypes = dict(build_filetypes())

        assert "*.mp4" in filetypes["All supported"]
        assert "*.pdf" in filetypes["All supported"]
        assert "*.png" in filetypes["All supported"]

    def test_groups_by_category(self):
        filetypes = dict(build_filetypes())

        assert filetypes["Videos"] == "*.mp4 *.wmv *.avi *.mkv *.mov *.flv"
        assert filetypes["PDFs"] == "*.pdf"
        assert "*.jpg" in filetypes["Images"]

    def test_excludes_presentations_from_type_groups(self):
        all_patterns = " ".join(pattern for label, pattern in build_filetypes() if label != "All files")
        assert "pptx" not in all_patterns

    def test_has_all_files_fallback(self):
        labels = [label for label, _ in build_filetypes()]

        assert "All files" in labels
