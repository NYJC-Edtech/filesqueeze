"""filesqueeze.state.enums

Enums for the conversion state machine.
"""


class EnumMeta(type):
    """Metaclass for Enum to enable iteration over class attributes."""

    def __iter__(cls):
        """Iterate over the enum members (class attributes).

        For nested enums (like Format), this returns the nested enum
        classes directly.
        For leaf enums (like Video), this returns an EnumValue wrapper.
        """
        from collections import namedtuple

        # Check if this is a nested enum (contains other Enum classes)
        has_nested_enums = any(
            isinstance(v, type) and issubclass(v, Enum) for k, v in cls.__dict__.items() if not k.startswith("_")
        )

        if has_nested_enums:
            # This is a nested enum like Format - return the nested enum classes
            return iter(
                (
                    v
                    for k, v in cls.__dict__.items()
                    if not k.startswith("_") and isinstance(v, type) and issubclass(v, Enum) and v is not cls
                )
            )
        else:
            # This is a leaf enum like Video - return EnumValue wrappers
            EnumValue = namedtuple("EnumValue", ["name", "value"])
            return iter((EnumValue(k, v) for k, v in cls.__dict__.items() if not k.startswith("_") and not callable(v)))

    def __getitem__(cls, key):
        """Support format['MP4'] syntax."""
        return cls.__dict__.get(key)


class Enum(metaclass=EnumMeta):
    """A custom string Enum class for bundling constants."""

    __slots__ = tuple()

    def __init__(self):
        raise SyntaxError("Enum class cannot be instantiated directly.")

    @classmethod
    def __contains__(cls, member: str) -> bool:
        """Check if a member is in the enum."""
        return member in cls.__dict__

    @classmethod
    def validate(cls, member: str) -> None:
        """Validate if a member is in the enum."""
        if member not in cls.__dict__:
            raise ValueError(f"{member!r} is not a valid member of {cls.__name__}.")


class Video(Enum):
    WMV = "wmv"
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    FLV = "flv"


class Slideshow(Enum):
    PPTX = "pptx"


class Document(Enum):
    PDF = "pdf"
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"


class Format(Enum):
    Video = Video
    Slideshow = Slideshow
    Document = Document


class Status(Enum):
    COMPLETE = "Done"
    COMPRESS = "Compress"
    CONVERT = "Convert"
    ANALYZE = "Analyze"
    PENDING = "Pending"
    ERROR = "Error"
