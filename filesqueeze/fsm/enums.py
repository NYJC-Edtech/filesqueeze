"""filesqueeze.state.enums

Enums for the conversion state machine.
"""

class Enum:
    """A custom string Enum class for bundling constants."""
    __slots__ = tuple()

    def __init__(self):
        raise SyntaxError("Enum class cannot be instantiated directly.")
    
    @classmethod
    def __contains__(cls, member: str) -> bool:
        """Check if a member is in the enum."""
        return member in cls.__dict__
    
    @classmethod
    def __iter__(cls):
        """Iterate over the enum members."""
        return iter(cls.__dict__.values())
    
    @classmethod
    def validate(cls, member: str) -> bool:
        """Validate if a member is in the enum."""
        if member not in cls.__dict__:
            raise ValueError(f"'{member!r}' is not a valid member of {cls.__name__}.")


class Video(Enum):
    WMV = 'wmv'
    MP4 = 'mp4'
    AVI = 'avi'


class Slideshow(Enum):
    PPTX = 'pptx'


class Format(Enum):
    Video = Video
    Slideshow = Slideshow


class Status(Enum):
    COMPLETE = 'Done'
    COMPRESS = 'Compress'
    CONVERT = 'Convert'
    ANALYZE = 'Analyze'
    PENDING = 'Pending'
    ERROR = 'Error'
