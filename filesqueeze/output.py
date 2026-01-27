"""filesqueeze.output

Output path generation and metadata handling.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config


def generate_output_path(
    input_path: Path,
    output_dir: Path,
    structure: str = 'flat',
    config: Optional[Config] = None
) -> Path:
    """Generate output path based on structure setting.

    Args:
        input_path: Input file path.
        output_dir: Output directory.
        structure: Output structure (flat, by_type, by_date, mirror).
        config: Optional Config object.

    Returns:
        Path to the output file.
    """
    # Get structure from config if not specified
    if config and not structure:
        structure = config.get('output.structure', 'flat')

    # Validate structure
    valid_structures = ['flat', 'by_type', 'by_date', 'mirror']
    if structure not in valid_structures:
        raise ValueError(f"Invalid structure: {structure}. Must be one of {valid_structures}")

    # Add compressed_ prefix to filename
    compressed_filename = f"compressed_{input_path.name}"

    # Generate output path based on structure
    if structure == 'flat':
        # All files in output root
        return output_dir / compressed_filename

    elif structure == 'by_type':
        # Organize by file type
        ext = input_path.suffix.lstrip('.').lower()

        # Determine type directory
        if ext in ['mp4', 'wmv', 'avi']:
            type_dir = 'video'
        elif ext in ['pdf']:
            type_dir = 'document'
        elif ext in ['jpg', 'jpeg', 'png']:
            type_dir = 'image'
        elif ext in ['pptx']:
            type_dir = 'slideshow'
        else:
            type_dir = 'other'

        return output_dir / type_dir / compressed_filename

    elif structure == 'by_date':
        # Organize by date (YYYY-MM-DD)
        # Use file modification time
        mtime = input_path.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        return output_dir / date_str / compressed_filename

    elif structure == 'mirror':
        # Preserve source structure relative to input root
        # For this, we need to know the input root
        # If input_path is relative, use it as-is
        # If input_path is absolute, we need the input_root from config
        if config:
            input_root = config.input_dir
        else:
            # Try to preserve relative structure
            input_root = Path('')

        if input_root and input_path.is_absolute():
            # Try to preserve relative path
            try:
                rel_path = input_path.relative_to(input_root)
                # Add compressed_ prefix to the final filename component
                return output_dir / rel_path.parent / f"compressed_{rel_path.name}"
            except ValueError:
                # input_path is not relative to input_root, fall back to flat
                return output_dir / compressed_filename
        else:
            # Use the relative path structure with compressed_ prefix
            return output_dir / input_path.parent / compressed_filename

    # Default to flat
    return output_dir / compressed_filename


def save_metadata(
    output_path: Path,
    metadata: dict,
    config: Optional[Config] = None
) -> None:
    """Save metadata alongside output file.

    Args:
        output_path: Path to the output file.
        metadata: Metadata dictionary to save.
        config: Optional Config object.
    """
    # Check if metadata saving is enabled
    if config:
        enabled = config.get('output.save_metadata', False)
    else:
        enabled = False

    if not enabled:
        return

    # Create metadata file path
    metadata_path = output_path.with_suffix('.json')

    # Save metadata
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)


def preserve_timestamps(
    input_path: Path,
    output_path: Path,
    config: Optional[Config] = None
) -> None:
    """Copy timestamps from input to output file.

    Args:
        input_path: Input file path.
        output_path: Output file path.
        config: Optional Config object.
    """
    # Check if timestamp preservation is enabled
    if config:
        enabled = config.get('output.preserve_timestamps', True)
    else:
        enabled = True

    if not enabled:
        return

    # Get input file timestamps
    stat = input_path.stat()
    atime = stat.st_atime
    mtime = stat.st_mtime

    # Set output file timestamps
    os.utime(output_path, (atime, mtime))


def ensure_output_dir(output_path: Path) -> None:
    """Ensure output directory exists.

    Args:
        output_path: Path to the output file.
    """
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)


def get_unique_output_path(
    output_path: Path,
    max_attempts: int = 1000
) -> Path:
    """Get a unique output path, adding suffix if file exists.

    Args:
        output_path: Desired output path.
        max_attempts: Maximum number of attempts to find unique path.

    Returns:
        Unique output path.

    Raises:
        RuntimeError: If unique path cannot be found.
    """
    if not output_path.exists():
        return output_path

    # Try adding suffixes
    stem = output_path.stem
    suffix = output_path.suffix
    parent = output_path.parent

    for i in range(1, max_attempts + 1):
        new_path = parent / f"{stem}_{i}{suffix}"
        if not new_path.exists():
            return new_path

    raise RuntimeError(f"Could not find unique output path: {output_path}")
