"""filesqueeze.ops.document

Document compression functions for PDF using Ghostscript.

This module provides PDF compression operations using Ghostscript.
It uses the system package for binary detection and logging.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

# Import from system package
from filesqueeze.system import get_binary_finder, logger


def get_ghostscript_path(config_path: str = '') -> str:
    """Get the Ghostscript executable path.

    Args:
        config_path: Path from config, or empty string to use PATH.

    Returns:
        Path to Ghostscript executable.

    Raises:
        RuntimeError: If Ghostscript is not found.

    Note:
        If config_path is provided and exists, it will be used.
        Otherwise, uses the registered BinaryFinder to auto-detect.
    """
    # If explicit path provided and it exists, use it
    if config_path and Path(config_path).exists():
        return config_path

    # Otherwise use registered finder
    finder = get_binary_finder()
    return finder.get_ghostscript_path()


def compress_pdf(
    infile: str,
    outfile: str,
    *,
    quality: str = 'ebook',
    compression_level: int = 2,
    ghostscript_path: str = '',
    config=None
) -> None:
    """Compress a PDF file using Ghostscript.

    Args:
        infile: Input PDF file path.
        outfile: Output PDF file path.
        quality: PDF quality setting (screen, ebook, printer, prepress, default).
        compression_level: Compression level (0-4).
        ghostscript_path: Optional path to Ghostscript executable.
        config: Optional Config object with settings.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If Ghostscript fails.
        ValueError: If quality setting is invalid.
    """
    from filesqueeze.system.decorators import trace_function
    from filesqueeze.system.config_adapters import DocumentConfig

    @trace_function
    def _compress_pdf(
        infile: str,
        outfile: str,
        *,
        quality: str = 'ebook',
        compression_level: int = 2,
        ghostscript_path: str = '',
        config=None
    ) -> None:
        # Use config adapter if config provided
        if config:
            doc_config = DocumentConfig(config)
            ghostscript_path = ghostscript_path or config.ghostscript_path
            timeout = doc_config.timeout
        else:
            timeout = 300

        # Map quality levels to Ghostscript PDFSETTINGS
        quality_settings = {
            'screen': '/screen',
            'ebook': '/ebook',
            'printer': '/printer',
            'prepress': '/prepress',
            'default': '/default'
        }

        # Validate quality parameter before trying to find Ghostscript
        if quality not in quality_settings:
            raise ValueError(f"Invalid quality setting: {quality}. Must be one of {list(quality_settings.keys())}")

        gs = get_ghostscript_path(ghostscript_path)

        cmd = [
            gs,
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={quality_settings[quality]}',
            f'-dCompressionLevel={compression_level}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-sOutputFile=' + outfile,
            infile,
        ]

        # Get input file size for comparison
        input_size = Path(infile).stat().st_size

        try:
            subprocess.run(cmd, timeout=timeout, check=True)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Ghostscript timeout compressing PDF: {infile}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ghostscript failed with return code {e.returncode}: {infile}")

        # Verify output file exists
        if not Path(outfile).exists():
            raise FileNotFoundError(f"Output file not created: {outfile}")

        # Verify compression actually reduced file size
        output_size = Path(outfile).stat().st_size
        if output_size >= input_size:
            import shutil
            # Compression didn't help, copy original instead
            shutil.copy2(infile, outfile)

    _compress_pdf(
        infile, outfile,
        quality=quality,
        compression_level=compression_level,
        ghostscript_path=ghostscript_path,
        config=config
    )


# Backward compatibility: re-export image operations from ops.image
# (historically, these were in document.py before extraction)
from filesqueeze.ops.image import compress_image, get_image_size
