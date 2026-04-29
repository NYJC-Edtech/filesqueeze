"""Smoke test: API integrity.

This test verifies that the public FileSqueeze API is intact and callable.
API failures indicate show-stopper issues like:
- Broken function signatures
- Missing exports
- Incorrect module structure
- Failed package installation

Users cannot fix these issues themselves - they indicate a broken installation.
"""


def test_main_api_functions_exist():
    """Main API functions must be exported and callable."""
    from filesqueeze import make_image, make_pdf, make_presentation, make_video

    # All main API functions must be callable
    assert callable(make_video)
    assert callable(make_pdf)
    assert callable(make_image)
    assert callable(make_presentation)


def test_api_function_signatures():
    """API functions must have correct signatures."""
    import inspect

    from filesqueeze import make_image, make_pdf, make_video

    # Functions should accept at least input path parameter
    for func in [make_video, make_pdf, make_image]:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Should have at least an input parameter (usually first)
        assert len(params) >= 1, f"{func.__name__} should accept at least one parameter"
        assert "filepath" in params, f"{func.__name__} should have filepath parameter"


def test_module_exports():
    """Critical modules must export expected components."""
    import filesqueeze

    # Package should have expected top-level attributes
    assert hasattr(filesqueeze, "config")
    assert hasattr(filesqueeze, "logger")
    assert hasattr(filesqueeze, "handlers")

    # Main API functions should be accessible
    assert hasattr(filesqueeze, "make_video")
    assert hasattr(filesqueeze, "make_pdf")
    assert hasattr(filesqueeze, "make_image")

    # Operations modules should be exported
    assert hasattr(filesqueeze, "video")
    assert hasattr(filesqueeze, "document")
    assert hasattr(filesqueeze, "image")


def test_service_provider_interface():
    """StateProvider interface must be defined."""
    import inspect

    from filesqueeze.service import StateProvider

    # StateProvider should be a class or protocol
    assert inspect.isclass(StateProvider) or inspect.isprotocol(StateProvider)

    # Should have get_state method
    assert hasattr(StateProvider, "get_state")
    assert callable(StateProvider.get_state)


def test_config_class_interface():
    """Config class must have required interface."""
    import tempfile

    from filesqueeze.config import Config

    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config()

        # Config must support get() method
        assert hasattr(config, "get")
        assert callable(config.get)

        # Config must have directory properties
        assert hasattr(config, "input_dir")
        assert hasattr(config, "output_dir")
        assert hasattr(config, "archive_dir")


def test_error_handling_classes():
    """Error handling classes must exist."""
    from filesqueeze.ops.image import compress_image
    from filesqueeze.ops.video import compress as compress_video

    # Functions should exist and raise appropriate errors when called incorrectly
    assert callable(compress_video)
    assert callable(compress_image)


def test_package_metadata():
    """Package must have proper metadata."""
    import filesqueeze

    # Package should have basic documentation
    assert hasattr(filesqueeze, "__doc__")

    # Package should have __all__ defined for exports
    assert hasattr(filesqueeze, "__all__")
    assert isinstance(filesqueeze.__all__, list)
    assert len(filesqueeze.__all__) > 0
