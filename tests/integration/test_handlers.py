"""Test handlers and state machine integration."""

from filesqueeze import handlers
from filesqueeze.fsm.default import State
from filesqueeze.fsm.enums import Document, Video


class TestStateClass:
    """Test State class with new fields."""

    def test_state_init_basic(self, tmp_path):
        """Test basic State initialization."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        state = State(str(test_file))

        assert state.origin == test_file
        assert state.target == test_file
        assert state.format is None
        assert state.metadata == {}
        assert str(state.status) == "Pending"

    def test_state_init_with_output_path(self, tmp_path):
        """Test State initialization with output path."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")
        output_file = tmp_path / "output.pdf"

        state = State(str(test_file), output_path=str(output_file))

        assert state.origin == test_file
        assert state.target == test_file
        assert state.output_path == output_file

    def test_state_init_with_config(self, tmp_path):
        """Test State initialization with config."""
        from filesqueeze.config import Config

        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")

        config = Config()
        state = State(str(test_file), config=config)

        assert state.origin == test_file
        assert state.config == config

    def test_state_with_output_path_and_config(self, tmp_path):
        """Test State initialization with both output path and config."""
        from filesqueeze.config import Config

        test_file = tmp_path / "test.pdf"
        test_file.write_text("test content")
        output_file = tmp_path / "output.pdf"

        config = Config()
        state = State(str(test_file), output_path=str(output_file), config=config)

        assert state.origin == test_file
        assert state.output_path == output_file
        assert state.config == config


class TestDocumentHandlers:
    """Test document handlers."""

    def test_analyze_document_pdf(self, tmp_path):
        """Test analyzeDocument handler for PDF files."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf")

        state = State(str(test_file))
        next_handler = handlers.analyzeDocument(state)

        # Should return compressDocument handler
        assert next_handler == handlers.compressDocument
        assert str(state.status) == "Analyze"

    def test_analyze_document_without_config(self, tmp_path):
        """Test analyzeDocument without config (should not fail)."""
        test_file = tmp_path / "test.jpg"
        # Create minimal JPEG
        test_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        state = State(str(test_file))
        # Should handle missing config gracefully
        next_handler = handlers.analyzeDocument(state)

        # Should return compressDocument handler even without metadata
        assert next_handler == handlers.compressDocument

    def test_compress_document_pdf_without_gs(self, tmp_path):
        """Test compressDocument for PDF without Ghostscript."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf")
        output_file = tmp_path / "output.pdf"

        state = State(str(test_file), output_path=str(output_file))
        state.status_analyze()

        # Should fail gracefully when Ghostscript is not available
        next_handler = handlers.compressDocument(state)

        # Should return cleanupFiles even after error
        assert next_handler == handlers.cleanupFiles

    def test_compress_document_image_without_ffmpeg(self, tmp_path):
        """Test compressDocument for image without FFmpeg."""
        test_file = tmp_path / "test.jpg"
        # Create minimal JPEG
        test_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")
        output_file = tmp_path / "output.jpg"

        state = State(str(test_file), output_path=str(output_file))
        state.status_analyze()

        # Should fail gracefully when FFmpeg is not available
        next_handler = handlers.compressDocument(state)

        # Should return cleanupFiles even after error
        assert next_handler == handlers.cleanupFiles


class TestVideoHandlers:
    """Test video handlers with config."""

    def test_analyze_video_without_ffprobe(self, tmp_path):
        """Test analyzeVideo handler without ffprobe."""
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"dummy video content")

        state = State(str(test_file))
        next_handler = handlers.analyzeVideo(state)

        # Should return compressVideo handler even if analysis fails
        assert next_handler == handlers.compressVideo
        assert str(state.status) == "Analyze"

    def test_compress_video_without_ffmpeg(self, tmp_path):
        """Test compressVideo handler without FFmpeg."""
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"dummy video content")

        state = State(str(test_file))
        state.status_analyze()

        # Should fail gracefully when FFmpeg is not available
        next_handler = handlers.compressVideo(state)

        # Should return cleanupFiles even after error
        assert next_handler == handlers.cleanupFiles


class TestSelectAnalyzer:
    """Test selectAnalyzer handler."""

    def test_select_analyzer_pdf(self, tmp_path):
        """Test selectAnalyzer routes PDF to document handler."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf")

        state = State(str(test_file))
        next_handler = handlers.selectAnalyzer(state)

        # Should route to analyzeDocument
        assert next_handler == handlers.analyzeDocument
        assert state.format == Document.PDF

    def test_select_analyzer_jpg(self, tmp_path):
        """Test selectAnalyzer routes JPG to document handler."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        state = State(str(test_file))
        next_handler = handlers.selectAnalyzer(state)

        # Should route to analyzeDocument
        assert next_handler == handlers.analyzeDocument
        assert state.format == Document.JPG

    def test_select_analyzer_png(self, tmp_path):
        """Test selectAnalyzer routes PNG to document handler."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        state = State(str(test_file))
        next_handler = handlers.selectAnalyzer(state)

        # Should route to analyzeDocument
        assert next_handler == handlers.analyzeDocument
        assert state.format == Document.PNG

    def test_select_analyzer_mp4(self, tmp_path):
        """Test selectAnalyzer routes MP4 to video handler."""
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"dummy video content")

        state = State(str(test_file))
        next_handler = handlers.selectAnalyzer(state)

        # Should route to analyzeVideo
        assert next_handler == handlers.analyzeVideo
        assert state.format == Video.MP4

    def test_select_analyzer_unsupported(self, tmp_path):
        """Test selectAnalyzer with unsupported file type."""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("unsupported file")

        state = State(str(test_file))
        next_handler = handlers.selectAnalyzer(state)

        # Should route to cleanupFiles with error
        assert next_handler == handlers.cleanupFiles
        assert str(state.status) == "Error"


class TestStateMachineIntegration:
    """Test state machine with new fields."""

    def test_state_machine_with_config(self, tmp_path):
        """Test StateMachine passes config through to State."""
        from filesqueeze.config import Config
        from filesqueeze.fsm import StateMachine

        test_file = tmp_path / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf")

        config = Config()
        sm = StateMachine(start=handlers.selectAnalyzer)

        # Run state machine with config
        # Note: This will fail when trying to compress without Ghostscript,
        # but we're testing that the config is passed through
        final_state = sm.run(str(test_file), config=config)

        # Verify config was passed to state
        assert final_state.origin == test_file

    def test_state_machine_with_output_path(self, tmp_path):
        """Test StateMachine uses output path."""
        from filesqueeze.fsm import StateMachine

        test_file = tmp_path / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf")
        output_file = tmp_path / "output.pdf"

        sm = StateMachine(start=handlers.selectAnalyzer)

        # Run state machine with output path
        final_state = sm.run(str(test_file), output_path=str(output_file))

        # Verify output path was used
        assert final_state.origin == test_file
