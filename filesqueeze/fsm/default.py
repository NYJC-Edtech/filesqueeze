"""filesqueeze.state.default

Default state class for the conversion pipeline.
"""

from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Any

from .enums import Status


class State:
    """State object for the conversion pipeline.

    IMPORTANT: This class uses read-only properties for state attributes.
    Do NOT try to assign to state.status directly - use the provided methods:
    - state.status_analyze()
    - state.status_convert()
    - state.status_compress()
    - state.status_complete()
    - state.error()

    Example:
        BAD:  state.status = "Error"  # Raises AttributeError
        GOOD: state.error("Error message")
    """

    __slots__ = ("__data",)

    def __init__(self, origin: PathLike, output_path: PathLike | None = None, config=None) -> None:
        self.__data: dict[str, Any] = {
            "origin": Path(origin),
            "status": Status.PENDING,
            "created": datetime.fromtimestamp(Path(origin).stat().st_ctime),
            "added": datetime.now(),
            "format": None,
            "target": Path(origin),
            "metadata": {},
            "output_path": Path(output_path) if output_path else None,
            "config": config,
        }

    def __setattr__(self, name: str, value: Any) -> None:
        # Prevent direct attribute assignment to catch bugs early
        if name == "_State__data":
            # Allow initialization of __data
            super().__setattr__(name, value)
        else:
            raise AttributeError(
                f"Cannot set attribute '{name}' directly. "
                f"Use the appropriate method instead (e.g., status_analyze(), error(), etc.)"
            )

    def __getattr__(self, attr: str) -> Any:
        # Read-only access to attributes in __data
        if attr == "_State__data":
            # This shouldn't happen normally, but just in case
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")
        if attr in self.__data:
            return self.__data[attr]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{attr}'. Use the appropriate method to modify state."
        )

    # Public getter methods for commonly accessed attributes
    # These provide explicit public API instead of relying on __getattr__
    def get_output_path(self) -> Path | None:
        """Get the output path for this file.

        Returns:
            Optional[Path]: Output path if set, None otherwise
        """
        return self.__data.get("output_path")

    def get_format(self) -> str | None:
        """Get the target format for conversion.

        Returns:
            Optional[str]: Format string if set, None otherwise
        """
        return self.__data.get("format")

    def set_format_value(self, format: str) -> None:
        """Set the target format for conversion.

        Args:
            format: Format string to set
        """
        self.__data["format"] = format

    def set_target(self, target: PathLike) -> None:
        """Set the target path for this file.

        Args:
            target: Path to target file
        """
        self.__data["target"] = Path(target)

    def status_analyze(self) -> None:
        """Set status to ANALYZE."""
        self.__data["status"] = Status.ANALYZE

    def status_convert(self) -> None:
        """Set status to CONVERT."""
        self.__data["status"] = Status.CONVERT

    def status_compress(self) -> None:
        """Set status to COMPRESS."""
        self.__data["status"] = Status.COMPRESS

    def status_complete(self) -> None:
        """Set status to COMPLETE."""
        self.__data["status"] = Status.COMPLETE

    def error(self, msg: str) -> None:
        """Set status to ERROR.

        Args:
            msg: Error message (currently not stored, but provided for API consistency)
        """
        self.__data["status"] = Status.ERROR

    def as_dict(self) -> dict[str, Any]:
        """Convert state to dictionary representation.

        Returns:
            Dictionary containing state data
        """
        return {
            "origin": str(self.origin),
            "status": str(self.status),
            "created": self.created,
            "added": self.added.isoformat(),
            "format": str(self.format),
            "target": str(self.target),
            "metadata": self.metadata.copy(),
        }

    def __repr__(self) -> str:
        return type(self).__name__ + "(" + ", ".join([f"{key}={value!r}" for key, value in self.__data.items()]) + ")"
