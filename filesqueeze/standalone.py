"""filesqueeze.standalone

Standalone (single-file) compression logic shared by the GUI dialog and CLI.

Standalone mode compresses one user-chosen file to a user-chosen destination,
using the same pipeline, quality settings, and naming conventions as
monitoring mode (``compressed_<stem>.<ext>``).

This module is intentionally free of tkinter imports so the logic can be
unit-tested headlessly; ``gui_compress`` layers the dialog UI on top.
"""

from pathlib import Path

from .config import Config
from .constants import FileExtensions
from .output import generate_output_path, get_unique_output_path

# Categories the standalone dialog can process. Presentations are detected
# (so a meaningful message can be shown) but not yet supported here.
CATEGORY_LABELS: dict[str, str] = {
    "video": "Video",
    "pdf": "PDF",
    "image": "Image",
    "presentation": "PowerPoint",
}

STANDALONE_UNSUPPORTED_MESSAGE = "PowerPoint files are not supported in standalone mode yet."


class UnsupportedFileTypeError(ValueError):
    """Raised when a file cannot be compressed in standalone mode."""


def detect_category(extension: str) -> str | None:
    """Map a file extension to a compression category.

    Args:
        extension: Extension with or without a leading dot (case-insensitive).

    Returns:
        One of "video", "pdf", "image", "presentation", or None if the
        extension is not supported at all.
    """
    ext = extension.lstrip(".").lower()
    if ext in FileExtensions.VIDEO:
        return "video"
    if ext in FileExtensions.DOCUMENT:
        return "pdf"
    if ext in FileExtensions.IMAGE:
        return "image"
    if ext in FileExtensions.PRESENTATION:
        return "presentation"
    return None


def output_extension_for(input_path: Path) -> str:
    """Determine the output file extension for an input file.

    Images that are not already JPG convert to JPG output; everything else
    keeps its own extension (mirrors monitoring-mode behaviour).

    Args:
        input_path: The file to be compressed.

    Returns:
        Output extension including the leading dot (e.g. ".jpg").
    """
    ext = input_path.suffix.lstrip(".").lower()
    if detect_category(ext) == "image" and ext not in FileExtensions.IMAGE_NATIVE_JPG:
        return ".jpg"
    return input_path.suffix


def predict_output_path(input_path: Path, destination_dir: Path) -> Path:
    """Predict the output path for a standalone compression.

    Uses the same ``compressed_<stem>.<ext>`` naming as monitoring mode so a
    file compressed either way ends up with the same name.

    Args:
        input_path: The file to be compressed.
        destination_dir: Directory the compressed file will be written to.

    Returns:
        The predicted output path (collisions are not resolved here; see
        :func:`resolve_final_output_path`).
    """
    return generate_output_path(
        input_path,
        destination_dir,
        structure="flat",
        output_ext=output_extension_for(input_path),
    )


def resolve_final_output_path(predicted: Path) -> tuple[Path, bool]:
    """Resolve name collisions for a predicted output path.

    Args:
        predicted: The desired output path.

    Returns:
        Tuple of (final path, renamed). ``renamed`` is True when an existing
        file forced an auto-rename (``_1``, ``_2``, ... appended).
    """
    if not predicted.exists():
        return predicted, False
    return get_unique_output_path(predicted), True


def compress_file(input_path: Path, output_path: Path, config: Config) -> Path:
    """Compress a single file with the standard pipeline.

    Args:
        input_path: File to compress (must exist; caller validates).
        output_path: Destination path, typically from
            :func:`resolve_final_output_path`.
        config: Configuration providing quality settings and binary paths.

    Returns:
        The path of the file actually produced (may differ from
        ``output_path`` in extension, e.g. an image whose original was kept).

    Raises:
        UnsupportedFileTypeError: If the file type cannot be compressed here.
        Exception: Pipeline errors propagate from make_video/make_pdf/make_image.
    """
    from filesqueeze import make_image, make_pdf, make_video

    ext = input_path.suffix.lstrip(".").lower()
    category = detect_category(ext)

    if category == "video":
        result_path = make_video(str(input_path), config=config, output_path=str(output_path))
    elif category == "pdf":
        result_path = make_pdf(str(input_path), config=config, output_path=str(output_path))
    elif category == "image":
        result_path = make_image(str(input_path), config=config, output_path=str(output_path))
    elif category == "presentation":
        raise UnsupportedFileTypeError(STANDALONE_UNSUPPORTED_MESSAGE)
    else:
        raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

    return Path(result_path)


def format_size(num_bytes: int | float) -> str:
    """Format a byte count for display (e.g. "412.3 MB").

    Args:
        num_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def describe_result(input_size: int, output_size: int) -> str:
    """Describe a compression outcome in one human-readable line.

    Args:
        input_size: Size of the original file in bytes.
        output_size: Size of the compressed file in bytes.

    Returns:
        Summary like "412.0 MB → 96.2 MB (77% smaller)" or a note when the
        output is not smaller than the input.
    """
    summary = f"{format_size(input_size)} → {format_size(output_size)}"
    if output_size < input_size:
        reduction = (1 - output_size / input_size) * 100
        return f"{summary} ({reduction:.0f}% smaller)"
    return f"{summary} (not smaller than the original)"


def build_filetypes() -> list[tuple[str, str]]:
    """Build the file-type filter list for the file open dialog.

    Presentations are excluded from the type groups (unsupported in
    standalone mode) but remain reachable via "All files" so the dialog can
    explain itself instead of silently hiding the user's file.

    Returns:
        List of (label, pattern) tuples for tkinter's askopenfilename.
    """
    standalone_extensions = FileExtensions.VIDEO + FileExtensions.DOCUMENT + FileExtensions.IMAGE

    def patterns(extensions: list[str]) -> str:
        return " ".join(f"*.{ext}" for ext in extensions)

    return [
        ("All supported", patterns(standalone_extensions)),
        ("Videos", patterns(FileExtensions.VIDEO)),
        ("PDFs", patterns(FileExtensions.DOCUMENT)),
        ("Images", patterns(FileExtensions.IMAGE)),
        ("All files", "*.*"),
    ]
