from enum import Enum

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
