"""File type registry for mapping extensions to processing strategies.

This module provides a centralized registry for mapping file extensions
to their appropriate processing functions, eliminating hardcoded mappings
and making it easier to add new file types.
"""

from typing import Callable, Optional
from pathlib import Path


class FileTypeRegistry:
    """Registry mapping file extensions to processing strategies.

    This class provides a centralized way to map file extensions to their
    corresponding processor functions, eliminating hardcoded if-else chains
    and making the system more maintainable.
    """

    # File type mappings
    FILE_PROCESSORS = {
        'video': ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv'],
        'pdf': ['pdf'],
        'image': ['jpg', 'jpeg', 'png'],
        'presentation': ['ppt', 'pptx']
    }

    def __init__(self):
        """Initialize the file type registry with processor mappings."""
        self._processor_map = {}

    def register_processor(self, file_type: str, processor_func: Callable, extensions: list) -> None:
        """Register a processor function for a file type.

        Args:
            file_type: Type identifier (e.g., 'video', 'pdf').
            processor_func: Function to call for processing this file type.
            extensions: List of file extensions for this type (e.g., ['mp4', 'avi']).
        """
        self._processor_map[file_type] = processor_func
        self.FILE_PROCESSORS[file_type] = extensions

    def get_processor(self, extension: str) -> Optional[Callable]:
        """Get the appropriate processor function for a file extension.

        Args:
            extension: File extension (e.g., 'mp4', 'pdf', 'jpg').

        Returns:
            Processor function for this extension, or None if not supported.

        Example:
            >>> registry = FileTypeRegistry()
            >>> registry.initialize_processors()
            >>> processor = registry.get_processor('mp4')
            >>> processor(file, config=config)
        """
        extension_lower = extension.lower()

        for file_type, extensions in self.FILE_PROCESSORS.items():
            if extension_lower in extensions:
                return self._processor_map.get(file_type)

        return None

    def is_supported(self, extension: str) -> bool:
        """Check if a file extension is supported.

        Args:
            extension: File extension to check.

        Returns:
            True if extension is supported, False otherwise.
        """
        return self.get_processor(extension) is not None

    def get_all_supported_extensions(self) -> list:
        """Get list of all supported file extensions.

        Returns:
            List of all supported extensions (lowercase, without dots).
        """
        all_extensions = []
        for extensions in self.FILE_PROCESSORS.values():
            all_extensions.extend(extensions)
        return all_extensions


# Global registry instance
_global_registry = None


def get_file_type_registry() -> FileTypeRegistry:
    """Get the global file type registry instance.

    Returns:
        The global FileTypeRegistry instance.

    Note:
        The registry is initialized with processor functions on first call.
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = FileTypeRegistry()
        _initialize_registry(_global_registry)

    return _global_registry


def _initialize_registry(registry: FileTypeRegistry) -> None:
    """Initialize the registry with processor functions.

    Args:
        registry: The FileTypeRegistry instance to initialize.

    Note:
        This function is called once to register all processor functions.
        Import is done here to avoid circular imports.
    """
    from . import make_video, make_pdf, make_image, make_presentation

    registry.register_processor('video', make_video, ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv'])
    registry.register_processor('pdf', make_pdf, ['pdf'])
    registry.register_processor('image', make_image, ['jpg', 'jpeg', 'png'])
    registry.register_processor('presentation', make_presentation, ['ppt', 'pptx'])