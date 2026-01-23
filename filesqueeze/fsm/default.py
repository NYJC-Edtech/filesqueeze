"""filesqueeze.state.default

Default state class for the conversion pipeline.
"""
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Optional

from .enums import Format, Status


class State:
    __slots__ = ('__data',)
    def __init__(self, origin: PathLike, output_path: Optional[PathLike] = None, config=None):
        self.__data = {
            'origin': Path(origin),
            'status': Status.PENDING,
            'created': datetime.fromtimestamp(Path(origin).stat().st_ctime),
            'added': datetime.now(),
            'format': None,
            'target': Path(origin),
            'metadata': {},
            'output_path': Path(output_path) if output_path else None,
            'config': config,
        }
    
    def __getattr__(self, attr):
        # Read-only access to attributes in __data
        if attr in self.__data:
            return self.__data[attr]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    # Public getter methods for commonly accessed attributes
    # These provide explicit public API instead of relying on __getattr__
    def get_output_path(self) -> Optional[Path]:
        """Get the output path for this file.

        Returns:
            Optional[Path]: Output path if set, None otherwise
        """
        return self.__data.get('output_path')

    def get_format(self) -> Optional[str]:
        """Get the target format for conversion.

        Returns:
            Optional[str]: Format string if set, None otherwise
        """
        return self.__data.get('format')

    def set_format_value(self, format: str):
        """Set the target format for conversion.

        Args:
            format: Format string to set
        """
        self.__data['format'] = format

    def set_target(self, target):
        self.__data['target'] = Path(target)
    
    def status_analyze(self):
        self.__data['status'] = Status.ANALYZE

    def status_convert(self):
        self.__data['status'] = Status.CONVERT

    def status_compress(self):
        self.__data['status'] = Status.COMPRESS

    def status_complete(self):
        self.__data['status'] = Status.COMPLETE

    def error(self, msg: str):
        self.__data['status'] = Status.ERROR

    def as_dict(self) -> dict:
        return {
            'origin': str(self.origin),
            'status': self.status,
            'created': self.created,
            'added': self.added.isoformat(),
            'format': str(self.format),
            'target': str(self.target),
            'metadata': self.metadata.copy(),
        }

    def __repr__(self) -> str:
        return (
            type(self).__name__ + '('
            + ', '.join(
                [f'{key}={value!r}' for key, value in self.__data.items()]
            )
            + ')'
        )


